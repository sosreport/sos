/*
 objectcontentmws.js - Foteos Macrides
   Initial: October 10, 2004 - Last Revised: November 22, 2004
 Simple script for using an HTML file as object content in overlibmws popups.
 Include WRAP and TEXTPADDING,0 in the overlib call to ensure that the width
 argument is respected (unless the CAPTION plus CLOSETEXT widths add up to more
 than the width argument, in which case you should increase the width argument).

 See http://www.macridesweb.com/oltest/overflow.html for demonstrations.
*/

function OLobjectContent(data, width, height, name) {
 return ('<object data="'+data+'" width="'+width+'" height="'+height+'"'
 +(name?' name="'+name+'" id="'+name+'"':'')+' type="text/html">'
 +'<div>[object not supported]</div></object>');
}
