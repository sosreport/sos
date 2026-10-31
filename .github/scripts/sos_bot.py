#!/usr/bin/env python3
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

"""sos-bot automation for pull requests on the sos GitHub repository.

``triage`` runs on pull_request_target events. It adds
``Status/Needs Review``, the ``Kind/*`` label of each sos component the PR
changes, and ``Kind/New plugin`` and ``Kind/Collection`` based on the changes
to plugins.

``lifecycle`` runs on a schedule. A PR without activity for 90 days gets a
nudge, after 180 days (and at least 90 days after the nudge) it is labeled
``Status/Abandoned``, and 90 days after that it is closed. Activity by bots,
including sos-bot itself, does not count.

Only the python standard library is used, and the GitHub token is read from
the ``GITHUB_TOKEN`` environment variable.
"""

import argparse
import ast
import base64
import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple
from datetime import datetime, timedelta, timezone

API_URL = 'https://api.github.com'

NEEDS_REVIEW = 'Status/Needs Review'
ABANDONED = 'Status/Abandoned'
NEW_PLUGIN = 'Kind/New plugin'
COLLECTION = 'Kind/Collection'

# PRs with any of these labels are waiting on maintainers, or on something
# outside of the author's control, and never age out
EXEMPT_LABELS = (
    'Status/Blocked',
    'Reviewed/Ready for Merge',
    'Reviewed/Needs 2nd Ack',
)

# Labels for the files a PR changes. With any(), a label is added if at least
# one changed file matches a pattern, with all() only if every changed file
# does. In these patterns, * also matches across directories.
PATH_LABELS = (
    # The Plugin() base class
    ('Kind/Plugin', any, ['sos/report/plugins/__init__.py']),
    # The SoSReport() class
    ('Kind/report', any, ['sos/report/__init__.py']),
    # SoSCollector(), SoSNode(), RemoteTransport(), Cluster() and subclasses
    ('Kind/collect', any, ['sos/collector/*']),
    ('Kind/cleaner', any, [
        'sos/cleaner/*',
        'man/en/sos-clean.1',
        'man/en/sos-mask.1',
        'tests/cleaner_tests/*',
    ]),
    ('Kind/Upload', any, [
        'sos/upload/*',
        'man/en/sos-upload.1',
    ]),
    ('Kind/Policy', any, ['sos/policies/*']),
    ('Kind/Documentation', all, [
        'docs/*',
        'man/*',
        '*.md',
    ]),
    ('Kind/Testing', all, [
        'tests/*',
        '.github/workflows/*',
        'tox.ini',
    ]),
    ('Kind/RedHat', any, [
        'sos/policies/distros/redhat.py',
        'sos/presets/redhat/*',
        'sos/upload/targets/redhat.py',
        'sos.spec',
    ]),
    ('Kind/Ubuntu', any, [
        'sos/policies/distros/ubuntu.py',
        'sos/policies/distros/debian.py',
        'sos/presets/ubuntu/*',
        'sos/upload/targets/ubuntu.py',
        'debian/*',
        'snap/*',
    ]),
)

# Plugin() methods that define what a plugin collects
COLLECTION_METHODS = (
    'add_cmd_output',
    'add_container_logs',
    'add_copy_spec',
    'add_device_cmd',
    'add_dir_listing',
    'add_env_var',
    'add_forbidden_path',
    'add_journal',
    'add_service_status',
    'add_string_as_file',
    'collect_cmd_output',
)

PLUGIN_RE = re.compile(r'^sos/report/plugins/(?!__init__\.py$)[^/]+\.py$')
HUNK_RE = re.compile(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')
COLLECTION_RE = re.compile(rf"\b({'|'.join(COLLECTION_METHODS)})\(")

# Issue events that mean a person did something with the PR. Others, such as
# 'mentioned' or 'subscribed', are side effects of comments, including ours.
ACTIVITY_EVENTS = (
    'assigned',
    'convert_to_draft',
    'demilestoned',
    'head_ref_force_pushed',
    'head_ref_restored',
    'labeled',
    'milestoned',
    'ready_for_review',
    'renamed',
    'reopened',
    'review_dismissed',
    'review_request_removed',
    'review_requested',
    'unassigned',
    'unlabeled',
)

NUDGE_MARKER = '<!-- sos-bot:nudge -->'

Thresholds = namedtuple('Thresholds', ['nudge', 'abandon', 'close'])
DEFAULT_THRESHOLDS = Thresholds(nudge=90, abandon=180, close=90)


def parse_time(value):
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(
        tzinfo=timezone.utc
    )


def is_bot(user):
    """Deleted accounts (no user) are treated like bots and ignored"""
    if not user:
        return True
    return user.get('type') == 'Bot' or user['login'].endswith('[bot]')


class GitHub():
    """Minimal client for the GitHub REST API of a single repository"""

    def __init__(self, repo, token, dry_run=False):
        self.repo = repo
        self.token = token
        self.dry_run = dry_run

    def _request(self, method, url, data=None):
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Accept', 'application/vnd.github+json')
        req.add_header('Authorization', f'Bearer {self.token}')
        req.add_header('X-GitHub-Api-Version', '2022-11-28')
        req.add_header('User-Agent', 'sos-bot')
        if body is not None:
            req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
            link = resp.headers.get('Link', '')
        return (json.loads(payload) if payload else None), link

    def get(self, path):
        return self._request('GET', f'{API_URL}/repos/{self.repo}/{path}')[0]

    def get_all(self, path):
        """GET every page of a list endpoint"""
        sep = '&' if '?' in path else '?'
        url = f'{API_URL}/repos/{self.repo}/{path}{sep}per_page=100'
        results = []
        while url:
            page, link = self._request('GET', url)
            results.extend(page)
            match = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = match.group(1) if match else None
        return results

    def get_file(self, path, ref):
        """Content of a text file at the given ref, or None"""
        try:
            data = self.get(f'contents/{urllib.parse.quote(path)}?ref={ref}')
            return base64.b64decode(data['content']).decode('utf-8')
        except (urllib.error.HTTPError, KeyError, TypeError, ValueError):
            return None

    def _write(self, method, path, data, description):
        if self.dry_run:
            print(f'  [dry-run] {description}')
            return
        print(f'  {description}')
        self._request(method, f'{API_URL}/repos/{self.repo}/{path}', data)

    def add_labels(self, number, labels):
        self._write('POST', f'issues/{number}/labels', {'labels': labels},
                    f'add labels: {", ".join(labels)}')

    def remove_label(self, number, label):
        name = urllib.parse.quote(label, safe='')
        self._write('DELETE', f'issues/{number}/labels/{name}', None,
                    f'remove label: {label}')

    def comment(self, number, body):
        self._write('POST', f'issues/{number}/comments', {'body': body},
                    'post comment')

    def close(self, number):
        self._write('PATCH', f'pulls/{number}', {'state': 'closed'},
                    'close pull request')


def path_labels(paths):
    """Labels for the components that a list of changed files belongs to"""
    labels = set()
    for label, match, patterns in PATH_LABELS:
        if paths and match(
                any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
                for path in paths):
            labels.add(label)
    return labels


def changed_lines(patch):
    """Line numbers of the removed lines, in the old version of the file, and
    of the added lines, in the new version
    """
    removed, added = set(), set()
    old = new = 0
    for line in patch.splitlines():
        hunk = HUNK_RE.match(line)
        if hunk:
            old, new = int(hunk.group(1)), int(hunk.group(2))
        elif line.startswith('+'):
            added.add(new)
            new += 1
        elif line.startswith('-'):
            removed.add(old)
            old += 1
        elif not line.startswith('\\'):
            old += 1
            new += 1
    return removed, added


def collection_calls(source):
    """Line ranges of the collection calls in plugin source, or None

    The source is only parsed, never run.
    """
    if source is None:
        return None
    try:
        return [
            (node.lineno, node.end_lineno)
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and
            isinstance(node.func, ast.Attribute) and
            node.func.attr in COLLECTION_METHODS
        ]
    except (SyntaxError, ValueError, RecursionError):
        return None


def changes_collection(path, patch, versions):
    """Whether a patch changes lines within a collection call

    :param path: the file the patch applies to
    :param patch: the patch from the pull request files API
    :param versions: a PullRequestFiles
    """
    removed, added = changed_lines(patch)
    for lines, get_source in ((added, versions.after),
                              (removed, versions.before)):
        if not lines:
            continue
        calls = collection_calls(get_source(path))
        if calls is None:
            # without usable source, look for calls on the changed lines
            return any(line.startswith(('+', '-')) and
                       COLLECTION_RE.search(line)
                       for line in patch.splitlines())
        if any(start <= line <= end
               for line in lines for start, end in calls):
            return True
    return False


class PullRequestFiles():
    """The versions of a file before and after the changes of a PR"""

    def __init__(self, gh, pr):
        self.gh = gh
        self.pr = pr
        self.merge_base = None

    def before(self, path):
        # patches are against the merge base, not the current base branch
        if self.merge_base is None:
            try:
                compare = self.gh.get(f"compare/{self.pr['base']['sha']}..."
                                      f"{self.pr['head']['sha']}")
                self.merge_base = compare['merge_base_commit']['sha']
            except (urllib.error.HTTPError, KeyError, TypeError):
                return None
        return self.gh.get_file(path, self.merge_base)

    def after(self, path):
        return self.gh.get_file(path, self.pr['head']['sha'])


def plugin_labels(files, versions):
    """Labels derived from the plugin files a PR adds or changes

    :param files: entries of the pull request files API
    :param versions: a PullRequestFiles
    """
    labels = set()
    for changed in files:
        path = changed['filename']
        if not PLUGIN_RE.match(path):
            continue
        if changed['status'] == 'added':
            labels.add(NEW_PLUGIN)
        elif changes_collection(path, changed.get('patch', ''), versions):
            labels.add(COLLECTION)
    return labels


def triage(gh, event):
    action = event['action']
    pr = event['pull_request']
    files = gh.get_all(f"pulls/{pr['number']}/files")
    labels = path_labels([changed['filename'] for changed in files])
    labels |= plugin_labels(files, PullRequestFiles(gh, pr))
    if action == 'ready_for_review' or (
            action in ('opened', 'reopened') and not pr['draft']):
        labels.add(NEEDS_REVIEW)
    current = {label['name'] for label in pr['labels']}
    missing = sorted(labels - current)
    print(f"#{pr['number']} ({action})")
    if missing:
        gh.add_labels(pr['number'], missing)
    return 0


def collect_activity(gh, pr, now):
    """Gather what the lifecycle decision needs to know about a PR

    Returns a list of (timestamp, login) for every activity by a person, the
    timestamps of the nudges sos-bot posted, and when Status/Abandoned was
    last applied (by anyone).
    """
    number = pr['number']
    author = pr['user']['login']
    activity = [(parse_time(pr['created_at']), author)]
    nudges = []
    abandoned_at = None

    for event in gh.get_all(f'issues/{number}/events'):
        when = parse_time(event['created_at'])
        label = (event.get('label') or {}).get('name')
        if event['event'] == 'labeled' and label == ABANDONED:
            abandoned_at = when
            continue
        if event['event'] in ACTIVITY_EVENTS and not is_bot(event['actor']):
            activity.append((when, event['actor']['login']))

    for comment in gh.get_all(f'issues/{number}/comments'):
        if is_bot(comment['user']):
            if NUDGE_MARKER in (comment['body'] or ''):
                nudges.append(parse_time(comment['created_at']))
        else:
            activity.append((parse_time(comment['updated_at']),
                             comment['user']['login']))

    for review in gh.get_all(f'pulls/{number}/reviews'):
        if review.get('submitted_at') and not is_bot(review['user']):
            activity.append((parse_time(review['submitted_at']),
                             review['user']['login']))

    for comment in gh.get_all(f'pulls/{number}/comments'):
        if not is_bot(comment['user']):
            activity.append((parse_time(comment['updated_at']),
                             comment['user']['login']))

    # GitHub does not expose when a branch was pushed. The committer date of
    # the head commit is reset by commit, amend and rebase, so it is a close
    # approximation. Dates in the future come from broken clocks; skip them.
    head = gh.get(f"commits/{pr['head']['sha']}")
    pushed = parse_time(head['commit']['committer']['date'])
    if pushed <= now:
        activity.append((pushed, author))

    return activity, nudges, abandoned_at


def decide(now, activity, author, nudges, abandoned_at, limits):
    """Decide the lifecycle step for one PR

    :param now: the current time
    :param activity: (timestamp, login) of all activity by people
    :param author: login of the PR author
    :param nudges: timestamps of sos-bot's nudge comments
    :param abandoned_at: when Status/Abandoned was applied, if it is applied
    :param limits: Thresholds, in days
    :returns: None, 'nudge', 'abandon', 'close' or 'unabandon'
    """
    if abandoned_at is not None:
        # Once abandoned, only the author coming back keeps the PR open, so
        # that maintainers can explain the label in a comment. Maintainers
        # can also simply remove the label.
        if any(when > abandoned_at for when, who in activity
               if who == author):
            return 'unabandon'
        if now - abandoned_at >= timedelta(days=limits.close):
            return 'close'
        return None

    last_activity = max(when for when, _ in activity)
    idle = now - last_activity
    nudged = max((when for when in nudges if when > last_activity),
                 default=None)
    if nudged is None:
        if idle >= timedelta(days=limits.nudge):
            return 'nudge'
        return None
    # Always give the author the full period between nudge and label, also
    # for PRs that were already long inactive when sos-bot first saw them
    if (idle >= timedelta(days=limits.abandon) and
            now - nudged >= timedelta(days=limits.abandon - limits.nudge)):
        return 'abandon'
    return None


def _days(value):
    return f'{value:g} days'


def apply_action(gh, pr, action, limits):
    number = pr['number']
    author = pr['user']['login']
    if action == 'nudge':
        gh.comment(number, (
            f"{NUDGE_MARKER}\n"
            f"@{author}, this pull request has had no activity for "
            f"{_days(limits.nudge)}. Please review the PR and any feedback "
            f"it has received, and push an update or leave a comment if you "
            f"would like to continue with it.\n\n"
            f"Without further activity, this PR will be marked "
            f"`{ABANDONED}` in {_days(limits.abandon - limits.nudge)}, and "
            f"closed {_days(limits.close)} after that."
        ))
    elif action == 'abandon':
        gh.add_labels(number, [ABANDONED])
        gh.comment(number, (
            f"This pull request has had no activity for "
            f"{_days(limits.abandon)} and is now marked `{ABANDONED}`. It "
            f"will be closed in {_days(limits.close)} unless @{author} "
            f"pushes an update or leaves a comment."
        ))
    elif action == 'close':
        gh.comment(number, (
            f"Closing this pull request, as it has been marked `{ABANDONED}` "
            f"for {_days(limits.close)} or more without further activity. If "
            f"you would like to continue this work, please leave a comment "
            f"asking for it to be reopened, or open a new pull request."
        ))
        gh.close(number)
    elif action == 'unabandon':
        gh.remove_label(number, ABANDONED)


def lifecycle(gh, now, limits):
    failed = False
    for pr in gh.get_all('pulls?state=open'):
        number = pr['number']
        labels = {label['name'] for label in pr['labels']}
        if labels.intersection(EXEMPT_LABELS):
            continue
        age = now - parse_time(pr['created_at'])
        if ABANDONED not in labels and age < timedelta(days=limits.nudge):
            continue
        try:
            activity, nudges, abandoned_at = collect_activity(gh, pr, now)
            if ABANDONED not in labels:
                abandoned_at = None
            elif abandoned_at is None:
                # Applied in a way that left no labeled event; start the
                # close period from the latest activity instead
                abandoned_at = max(when for when, _ in activity)
            action = decide(now, activity, pr['user']['login'], nudges,
                            abandoned_at, limits)
            if action:
                print(f'#{number}: {action}')
                apply_action(gh, pr, action, limits)
        except urllib.error.HTTPError as err:
            print(f'#{number}: GitHub API error: {err}', file=sys.stderr)
            failed = True
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY'),
                        help='OWNER/REPO, defaults to $GITHUB_REPOSITORY')
    parser.add_argument('--dry-run', action='store_true',
                        help='only report what would be changed')
    commands = parser.add_subparsers(dest='command', required=True)
    triage_cmd = commands.add_parser('triage', help='label a pull request')
    triage_cmd.add_argument('--event',
                            default=os.environ.get('GITHUB_EVENT_PATH'),
                            help='event payload, defaults to '
                                 '$GITHUB_EVENT_PATH')
    life_cmd = commands.add_parser('lifecycle',
                                   help='process inactive pull requests')
    for field in Thresholds._fields:
        life_cmd.add_argument(f'--{field}-days', type=float,
                              default=getattr(DEFAULT_THRESHOLDS, field))
    args = parser.parse_args()

    token = os.environ.get('GITHUB_TOKEN')
    if not token or not args.repo:
        parser.error('GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are '
                     'required')
    ellingson = GitHub(args.repo, token, dry_run=args.dry_run)

    if args.command == 'triage':
        if not args.event:
            parser.error('--event (or GITHUB_EVENT_PATH) is required')
        with open(args.event, encoding='utf-8') as event_file:
            return triage(ellingson, json.load(event_file))
    limits = Thresholds(args.nudge_days, args.abandon_days, args.close_days)
    return lifecycle(ellingson, datetime.now(timezone.utc), limits)


if __name__ == '__main__':
    sys.exit(main())
