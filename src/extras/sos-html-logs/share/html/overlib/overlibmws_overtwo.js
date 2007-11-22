/*
 overlibmws_overtwo.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For support of the popups-within-a-popup feature.
   Initial: July 14, 2003 - Last Revised: July 7, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
OLregCmds('label2');

// DEFAULT CONFIGURATION
if(OLud('label2'))var ol_label2="";
// END CONFIGURATION

var o3_label2="",OLshowingsticky2=0,over2=null,OLp1over=null,bkdrop2=null,OLp1bkdrop=null,
OLp1scroll=0,OLp1X=0,OLp1Y=0,OLp1If=null,OLp1IfShadow=null,OLp1bubbleHt=0,OLp1exclusive=0,
OLp1modal=0,OLp1fiIdx= -1,OLp1Hover=0;

function OLloadOvertwo(){
OLload('label2');
}

function OLparseOvertwo(pf,i,ar){
var k=i,q=OLparQuo;
if(k<ar.length){
if(ar[k]==LABEL2){q(ar[++k],pf+'label2');return k;}}
return -1;
}

// PUBLIC FUNCTIONS
function overlib2(){
var ar=arguments;if(over2)cClick2();if(!OLshowingsticky||ar.length==0)return false;
if(OLtimerid>0){clearTimeout(OLtimerid);OLtimerid=0;};if(OLshowid>0){clearTimeout(OLshowid);
OLshowid=0;}if(OLdelayid>0){clearTimeout(OLdelayid);OLdelayid=0;}
if(typeof over.onmouseover!='undefined'&&over.onmouseover!=null){OLp1Hover=1;OLhover=0;
over.onmouseover=null;}else OLp1Hover=0;OLp1over=null;OLp1scroll=(OLscrollPI&&o3_scroll?1:0);
if(OLp1scroll){OLp1X=over.scroll.x;OLp1Y=over.scroll.y;OLclearScroll();o3_scroll=0;}
if(OLfunctionPI)o3_function=ol_function;if(OLdraggablePI&&o3_draggable)OLclearDrag();
OLp1exclusive=(OLexclusivePI&&o3_exclusive?1:0);OLp1modal=(OLmodalPI&&o3_modal?1:0);
if((OLiframePI)&&OLifsP1){OLp1If=OLifsP1;OLifsP1=null;if(OLifsSh){OLp1IfShadow=OLifsSh;
OLifsSh=null;}}else{OLp1If=null;OLp1IfSh=null}OLpullP1(OLo2c(1));
if(OLbubblePI)OLp1bubbleHt=OLbubbleHt;if(OLfilterPI){OLp1fiIdx=OLfiIdx;
if(!OLie55&&o3_filter)OLopOv(o3_filteropacity);}
OLload(OLo2c(0));o3_label2=ol_label2;OLparseTokens('o3_',ar);OLpushP1(OLp1co);
if(OLexclusivePI)o3_exclusive=OLp1exclusive;if(o3_decode)OLdecode();
if(OLbubblePI)OLchkForBubbleEffect();if(o3_autostatus==2&&o3_cap!="")o3_status=o3_cap;
else if(o3_autostatus==1&&o3_text!="")o3_status=o3_text;
if(o3_delay==0)OLdispP2();else OLdelayid=setTimeout("OLdispP2()",o3_delay);
if(o3_status!=""){self.status=o3_status;return true;}
else if(!(OLop7&&event&&event.type=='mouseover'))return false;
}

function nd2(){
if(OLshowingsticky2)return false;return cClick2();
}

function cClick2(){
if(!over2||over!=over2)return false;
if(OLtimerid>0){clearTimeout(OLtimerid);OLtimerid=0;}
if(OLshowid>0){clearTimeout(OLshowid);OLshowid=0;}
if(OLp1over&&OLp1over!=OLmkLyr()){OLp1over=null;over2=null;return false;}
OLhover=0;over.onmouseover=null;OLhideObjectP2(over);
OLshowingsticky2=0;if(OLp1bkdrop){bkdrop=OLp1bkdrop;OLp1bkdrop=null;}
if(OLp1over){over=OLp1over;OLp1over=null;}
if((OLiframePI)&&OLp1If){OLifsP1=OLp1If;OLp1If=null;
if(OLp1IfShadow){OLifsSh=OLp1IfShadow;OLp1IfShadow=null;}}
OLpushP1(OLo2c(1));if(OLbubblePI){OLbubbleHt=OLp1bubbleHt;OLp1BubbleHt=0;}
if(OLfilterPI)OLfiIdx=OLp1fiIdx;var o=OLgetRefById();if(o&&o==over){
if(OLp1scroll){o3_scroll=1;OLp1scroll=0;OLchkScroll(OLp1X,OLp1Y);}else o3_scroll=0;
if(OLdraggablePI)OLcheckDrag();if(OLp1exclusive){o3_exclusive=1;OLp1exclusive=0;}
if(OLhidePI)OLhideUtil(0,1,1,0,0,0);
if(o3_autostatus==2&&o3_cap!="")o3_status=o3_cap;
else if(o3_autostatus==1&&o3_text!="")o3_status=o3_text;
if(OLp1Hover){OLoptMOUSEOFF(1);OLp1Hover=0;OLhover=1;}
if(o3_status!="")self.status=o3_status;}
if(OLmodalPI&&!OLp1modal)OLclearModal();OLp1modal=0;
return false;
}

// SUPPORT FUNCTIONS
function OLpullP1(c){var i,m=c.split(',');for(i=0;i<m.length;i++)eval('OLp1'+m[i]+'=o3_'+m[i]);}
function OLpushP1(c){var i,m=c.split(',');for(i=0;i<m.length;i++)eval('o3_'+m[i]+'=OLp1'+m[i]);}
function OLo2c(a){return OLp1or2+(a?','+OLp1:'')+(OLbubblePI?','+OLbubbleCmds:'')
+(OLdraggablePI?','+OLdraggableCmds:'')+(OLfilterPI?','+OLfilterCmds:'')+(OLmodalPI?','
+OLmodalCmds:'')+(OLprintPI?','+OLprintCmds:'')+(OLshadowPI?','+OLshadowCmds:'');}

function OLdispP2(){
var o=(OLns4?over:over.style),zI=parseInt(o.zIndex)+2;
o3_delay=0;if(!(over2=OLmkLyr('overDiv2',o3_frame,zI)))return;
OLp1over=over;over=over2;if(OLmodalPI&&!OLp1modal)OLchkModal();if(OLbubblePI)OLbubbleHt=0;
if(o3_frame==self){if(o3_noclose)OLoptMOUSEOFF(0);else if(o3_mouseoff)OLoptMOUSEOFF(1);}
if(o3_sticky)OLshowingsticky2=1;OLdoLyr();
if(o3_timeout>0){if(OLtimerid>0)clearTimeout(OLtimerid);
OLtimerid=setTimeout("cClick2()",o3_timeout);o3_timeout=0;}
if(o3_ref){OLrefXY=OLgetRefXY(o3_ref);if(OLrefXY[0]==null){o3_ref='';o3_midx=0;o3_midy=0;}}
if(OLshadowPI&&o3_shadow){OLp1bkdrop=bkdrop;bkdrop=bkdrop2;OLinitShadow();}
if(OLiframePI){OLinitIfs();OLdispIfs();}if(OLfilterPI)OLinitFilterLyr(2);
if(OLshadowPI&&o3_shadow)OLdispShadow();OLplaceLayer();
OLshowid=setTimeout("OLshowObjectP2(over2)",1);OLallowmove=(o3_sticky||o3_nofollow)?0:1;
}

function OLshowObjectP2(o){
OLshowid=0;if(o)o=(OLns4?o:o.style);
if(((OLfilterPI)&&!OLchkFilter(o,2))||!OLfilterPI)o.visibility="visible";
if(OLshadowPI)OLshowShadow();if(OLiframePI&&OLifsP2)OLifsP2.style.visibility="visible";
if(OLhidePI)OLhideUtil(1,1,0);if(OLdraggablePI)OLcheckDrag();
}

function OLhideObjectP2(o){
if(OLshowid>0){clearTimeout(OLshowid);OLshowid=0;}
if(OLtimerid>0){clearTimeout(OLtimerid);OLtimerid=0;}o3_timeout=0;
if(OLdelayid>0){clearTimeout(OLdelayid);OLdelayid=0;}o3_delay=0;
if(o&&o==OLgetRefById('overDiv2')){if(OLscrollPI)OLclearScroll();if(OLdraggablePI)OLclearDrag();
if(OLfilterPI)OLcleanupFilter(o,2);if(OLshadowPI)OLhideShadow();var os=(OLns4)?o:o.style;
if(((OLfilterPI)&&!OLchkFadeOut2(os))||!OLfilterPI){os.visibility="hidden";
if(!OLie55||!OLfilterPI||!o3_filter||o3_fadeout<0)o.innerHTML='';}
if(OLiframePI&&OLifsP2)OLifsP2.style.visibility="hidden";}
OLallowmove=o3_nofollow=0;o3_label2=ol_label2;
}

OLregRunTimeFunc(OLloadOvertwo);
OLregCmdLineFunc(OLparseOvertwo);

OLovertwoPI=1;
OLloaded=1;
