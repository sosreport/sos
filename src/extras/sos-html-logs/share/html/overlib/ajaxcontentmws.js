/*
 ajaxcontentmws.js - Foteos Macrides (author and Copyright holder)
    Initial: June 22, 2006 - Last Revised: March 2, 2007
 Wrapper function set for getting and using the responseText and / or
 responseXML from a GET or POST XMLHttpRequest, which can be used to
 generate dynamic content for overlib or overlib2 calls, or to modify
 the content of a displayed STICKY popup dynamically.

 For GET Use:
       onmouseover="return OLgetAJAX(url, command, delay, css);"
       onmouseout="OLclearAJAX();"  (if delay > 0)
 or:
       onclick="OLgetAJAX(url, command, 0, css); return false;"
 or:
       onload="OLgetAJAX(url, command, 0, css);
 
 Where:
       url (required)
 is a quoted string, or unquoted string variable name or array entry, with
 the full, relative, or partial URL for a file or a server-side script (php,
 asp, or cgi, e.g. perl), and may have a query string appended (e.g.,
 'http://my.domain.com/scripts/myScript.php?foo=bar&life=grand').
 And:
       command (required)
 is the function reference (unquoted name without parens) of a function to
 be called when the server's response has been received (it could instead be
 an inline function, i.e., defined within the 2nd argument, or a quoted string
 for a function with parens and any args)
 And:
       delay (may be omitted unless css is included)
 is an unquoted number indicating the number of millisecs to wait before
 initiating an XMLHttpRequest GET request. It should be 0 when using onclick
 or onload, but may be a modest value such as 300 for onmouseover to avoid
 any chatter of requests. When used with onmouseover, include:
       onmouseout="OLclearAJAX();"
 to clear the request if the user does not hover for at least that long.  If
 the popup is not STICKY, include an nd or nd2 call, e.g.,
       onmouseout="OLclearAJAX(); nd();"
 And:
       css (may be omitted)
 is a quoted string with the CSS class (e.g. 'ovfl510' for
 .ovfl510 {width:510px; height:145px; overflow:auto; ...} ) for a div to
 encase the responseText and set the width, height and scrollbars in the
 main text area of the popup, or the unquoted number 0 if no encasing div
 is to be used.

 For POST substitute OLpostAJAX(url, qry, command, delay, css);
 Where
       qry (required)
 is the string to be posted, typically a query string (without a lead ?)
 and the other arguments are as above.

 See http://www.macridesweb.com/oltest/AJAX.html for more information.
*/

// Initialize our global variables for this function set.
var OLhttp=false,OLcommandAJAX=null,OLdelayidAJAX=0,OLclassAJAX='',
OLresponseAJAX='',OLdebugAJAX=false;

// Create a series of wrapper functions (e.g. OLcmdT#() for  ones which
// use OLhttp.responseText via the OLresponseAJAX global, and OLcmdX#()
// for ones which use OLhttp.responseXML) whose reference (unquoted name
// without parens) is the 2nd argument in OLgetAJAX(url,command,delay,css)
// calls.  This one is for the first example in the AJAX.html support
// document, to use the OLresponseAJAX global as the lead argument for an
// overlib popup. Put your functions in the head, or in another imported
// .js file, so that they will not be affected by updates of this .js file.
//
function OLcmdExT1() {
 return overlib(OLresponseAJAX, TEXTPADDING,0, CAPTIONPADDING,4,
  CAPTION,'Example with AJAX content via <span '
  +'class="yellow">responseText</span>.&nbsp; Popup scrolls with the window.',
  WRAP, BORDER,2, STICKY, CLOSECLICK, SCROLL,
  MIDX,0, RELY,100,
  STATUS,'Example with AJAX content via responseText of XMLHttpResponse');
}

// Alert for old browsers which lack XMLHttpRequest support. 
function OLsorryAJAX() {
 alert('Sorry, AJAX is not supported by your browser.');
 return false;
}

// Check 2nd arg for function
function OLchkFuncAJAX(ar){
 var t=typeof ar;return (((t=='function'))||((t=='string')&&(/.+\(.*\)/.test(ar))));
}

// Alert for bad 2nd argument
function OLnotFuncAJAX(m) {
  if(over)cClick();
  alert('The 2nd arg of OL'+m+'AJAX is not a function reference, nor an inline function, '
  +'nor a quoted string with a function indicated.');
  return OLclearAJAX();
}

// Alert for indicating an XMLHttpRequest network error.
function OLerrorAJAX() {
 alert('Network error '+OLhttp.status+'. Try again later.');
 return false;
}

// Returns a new XMLHttpRequest object, or false for older browsers
// which did not yet support it.  Called as OLhttp=OLnewXMLHttp() via
// the OLgetAJAX(url,command,delay,css) wrapper function.
//
function OLnewXMLHttp() {
 var f=false,req=f;
 if(window.XMLHttpRequest)eval(new Array('try{',
 'req=new XMLHttpRequest();','}catch(e){','req=f;','}').join('\n'));
 /*@cc_on @if(@_jscript_version>=5)if(!req)
 eval(new Array('try{','req=new ActiveXObject("Msxml2.XMLHTTP");',
 '}catch(e){','try{','req=new ActiveXObject("Microsoft.XMLHTTP");',
 '}catch(e){','req=f;','}}').join('\n')); @end @*/
 return req;
}

// Handle the OLhttp.responseText string from the XMLHttpRequest object.
function OLdoAJAX() {
 if(OLhttp.readyState==4){
  if(OLdebugAJAX)alert(
    'OLhttp.status = '+OLhttp.status+'\n'
   +'OLhttp.statusText = '+OLhttp.statusText+'\n'
   +'OLhttp.getAllResponseHeaders() = \n'
   +OLhttp.getAllResponseHeaders()+'\n'
   +'OLhttp.getResponseHeader("Content-Type") = '
   +OLhttp.getResponseHeader("Content-Type")+'\n');
  if(!OLhttp.status||OLhttp.status==200){
   OLresponseAJAX=OLclassAJAX?'<div class="'+OLclassAJAX+'">':'';
   OLresponseAJAX += OLhttp.responseText;
   OLresponseAJAX += OLclassAJAX?'</div>':'';
   if(OLdebugAJAX)alert('OLresponseAJAX = \n'+OLresponseAJAX);
   OLclassAJAX=0;
   return (typeof OLcommandAJAX=='string')?eval(OLcommandAJAX):OLcommandAJAX();
  }else{
   OLclassAJAX=0;
   return OLerrorAJAX();
  }
 }
}

// Actually make the request initiated via OLgetAJAX or OLpostAJAX, or
// invoke a "permission denied" alert if a cross-domain URL was used.
function OLsetAJAX(url,qry) {
 qry=(qry||null);var s='',m=(qry)?'POST':'GET';
 OLdelayidAJAX=0;eval(new Array('try{','OLhttp.open(m,url,true);',
 '}catch(e){','s=e','OLhttp=false;','}').join('\n'));if(!OLhttp){
 alert(s+'\n(Cross-domain access not permitted)');return false;}if(qry)
 OLhttp.setRequestHeader('Content-type','application/x-www-form-urlencoded');
 OLhttp.onreadystatechange=OLdoAJAX;
 OLhttp.send(qry);
}

// Clear or abort any delayed OLsetAJAX call or pending request. 
function OLclearAJAX() {
 if(OLdelayidAJAX){clearTimeout(OLdelayidAJAX);OLdelayidAJAX=0;}
 if(OLhttp&&!OLdebugAJAX){OLhttp.abort();OLhttp=false;}
 return false;
}

// Load a new XMLHttpRequest object into the OLhttp global, load the
// OLcommandAJAX and OLclassAJAX globals, and initiate a GET request
// via OLsetAJAX(url) to populate OLhttp.
function OLgetAJAX(url,command,delay,css) {
 if(!OLchkFuncAJAX(command))return OLnotFuncAJAX('get');
 OLclearAJAX();OLhttp=OLnewXMLHttp();if(!OLhttp)return OLsorryAJAX();
 OLcommandAJAX=command;delay=(delay||0);css=(css||0);OLclassAJAX=css;
 if(delay)OLdelayidAJAX=setTimeout("OLsetAJAX('"+url+"')",delay);
 else OLsetAJAX(url);
}

// Load a new XMLHttpRequest object into the OLhttp global, load the
// OLcommandAJAX and OLclassAJAX globals, and initiate a POST request
// via OLsetAJAX(url,qry) to populate OLhttp.
function OLpostAJAX(url,qry,command,delay,css) {
 if(!OLchkFuncAJAX(command))return OLnotFuncAJAX('post');
 OLclearAJAX();OLhttp=OLnewXMLHttp();if(!OLhttp)return OLsorryAJAX();
 qry=(qry||0);OLcommandAJAX=command;delay=(delay||0);css=(css||0);OLclassAJAX=css;
 if(delay)OLdelayidAJAX=setTimeout("OLsetAJAX('"+url+"','"+qry+"')",delay);
 else OLsetAJAX(url,qry);
}
