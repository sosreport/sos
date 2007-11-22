/*
 iframecontentmws.js - Foteos Macrides (author and copyright holder)
   Initial: October 10, 2004 - Last Revised: November 11, 2006
 Scripts for using HTML documents as iframe content in overlibmws popups.

 See http://www.macridesweb.com/oltest/IFRAME.html
 and http://www.macridesweb.com/oltest/AJAX.html#ajaxex3
 for more information.
*/

/*
 Use as lead argument in overlib or overlb2 calls.  Include WRAP and
 TEXTPADDING,0 in the call to ensure that the width arg is respected (unless
 the CAPTION plus CLOSETEXT widths add up to more than the width arg, in which
 case you should increase the width arg).  The name arg should be a unique
 string for each popup with iframe content in the document.  The frameborder
 arg should be 1 (browser default if omitted) or 0.  The scrolling arg should
 be 'auto' (default if omitted), 'yes' or 'no'.
*/
function OLiframeContent(src, width, height, name, frameborder, scrolling) {
 return ('<iframe src="'+src+'" width="'+width+'" height="'+height+'"'
 +(name!=null?' name="'+name+'" id="'+name+'"':'')
 +(frameborder!=null?' frameborder="'+frameborder+'"':'')
 +' scrolling="'+(scrolling!=null?scrolling:'auto')
 +'"><div>[iframe not supported]</div></iframe>');
}

/*
 Swap the src if we are iframe content.  The name arg should be the same
 string as in the OLiframeContent function for the popup.  The src arg is
 a partial, relative, or complete URL for the document to be swapped in.
*/
function OLswapIframeSrc(name, src){
 if(parent==self){
  alert(src+'\n\n is only for iframe content');
  return;
 }
 var o=parent.OLgetRef(name);
 if(o)o.src=src;
 else alert(src+'\n\n is not available');
}

/*
 Emulate the Back button if we are iframe content.  Use only in documents
 which are swapped in by using the OLswapIframeSrc function.
*/
function OLiframeBack(){
 if(parent==self){
  alert('This feature is only for iframe content');
  return;
 }
 history.back();
}
