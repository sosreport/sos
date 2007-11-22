/*
 overlibmws_scroll.js plug-in module - Copyright Foteos Macrides 2002-2007. All rights reserved.
  For support of the SCROLL feature.
  Initial: October 20, 2002 - Last Revised: January 1, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
OLregCmds('scroll');

// DEFAULT CONFIGURATION
if(OLud('scroll'))var ol_scroll=0;
// END CONFIGURATION

var o3_scroll=0,OLscrollRefresh=100;

function OLloadScroll(){
OLload('scroll');
}

function OLparseScroll(pf,i,ar){
var k=i;
if(k<ar.length){if(Math.abs(ar[k])==SCROLL){OLtoggle(ar[k],pf+'scroll');return k;}}
return -1;
}

function OLchkScroll(X,Y){
if(o3_scroll){if(!OLshowingsticky||
(OLovertwoPI&&over==over2&&!OLshowingsticky2)||
(OLdraggablePI&&o3_draggable&&o3_frame==self)||
(o3_relx==null&&o3_midx==null)||(o3_rely==null&&o3_midy==null))o3_scroll=0;
else if(typeof over.scroll=='undefined'||over.scroll.canScroll)
over.scroll=new OLsetScroll(X,Y,OLscrollRefresh);}
}

function OLsetScroll(X,Y,refresh){
if(o3_scroll){this.canScroll=0;this.refresh=refresh;this.x=X;this.y=Y;
this.timer=setTimeout("OLscrollReposition()",this.refresh);}
}

function OLclearScroll(){
if(o3_scroll){if(typeof over.scroll=='undefined'){o3_scroll=0;return;}
over.scroll.canScroll=1;if(over.scroll.timer){
clearTimeout(over.scroll.timer);over.scroll.timer=null;}}
}

function OLscrollReposition(){
var o=over,oD=(OLovertwoPI&&over==over2?'overDiv2':'overDiv');
if(o3_scroll&&o&&o==OLgetRefById(oD)){var X,Y,pgLeft,pgTop;
pgLeft=(OLie4)?OLfd().scrollLeft:o3_frame.pageXOffset;
pgTop=(OLie4)?OLfd().scrollTop:o3_frame.pageYOffset;
X=(o.pageX?o.pageX:o.style.left?o.style.left:0)-pgLeft;
Y=(o.pageY?o.pageY:o.style.top?o.style.top:0)-pgTop;
if(X!=o.scroll.x||Y!=o.scroll.y){
OLrepositionTo(o,pgLeft+o.scroll.x,pgTop+o.scroll.y);
if(OLshadowPI)OLrepositionShadow(pgLeft+o.scroll.x,pgTop+o.scroll.y);
if(OLiframePI)OLrepositionIfs(pgLeft+o.scroll.x,pgTop+o.scroll.y);
if(OLhidePI)OLhideUtil(0,1,1,0,0,0);}
o.scroll.timer=setTimeout("OLscrollReposition()",o.scroll.refresh);}
}

OLregRunTimeFunc(OLloadScroll);
OLregCmdLineFunc(OLparseScroll);

OLscrollPI=1;
OLloaded=1;
