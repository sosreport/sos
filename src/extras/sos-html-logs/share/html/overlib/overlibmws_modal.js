/*
 overlibmws_modal.js plug-in module - Copyright Foteos Macrides 2006-2007. All rights reserved.
   For support of the MODAL feature.
   Initial: November 15, 2006 - Last Revised: September 22, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;var OLmodalCmds='modal,modalcolor,modalopacity';OLregCmds(OLmodalCmds);

// DEFAULT CONFIGURATION
if(OLud('modal'))var ol_modal=0;
if(OLud('modalcolor'))var ol_modalcolor="#bbbbbb";
if(OLud('modalopacity'))var ol_modalopacity=40;
// END CONFIGURATION

var o3_modal=0,o3_modalcolor="#bbbbbb",o3_modalopacity=40;

function OLloadModal(){
OLload(OLmodalCmds);
}

function OLparseModal(pf,i,ar){
var k=i;if(k<ar.length){
if(Math.abs(ar[k])==MODAL){OLtoggle(ar[k],pf+'modal');return k;}
if(ar[k]==MODALCOLOR){OLparQuo(ar[++k],pf+'modalcolor');return k;}
if(ar[k]==MODALOPACITY){OLpar(ar[++k],pf+'modalopacity');return k;}}
return -1;
}

var OLmMask=null,OLmIframe=null,OLmMaskOn=0,OLmSelectOK=(OLie55||OLop7||OLgek>=20030624)?1:0,
OLmRoot='html',OLmGotSc=0,OLmScLeft=0,OLmScTop=0,OLmKDH=null,OLmTI=new Array(),
OLmTT=new Array("a","button","iframe","input","select","textarea"),OLmEdit=0;	

function OLchkModal(){
if(o3_modal){if(o3_sticky&&!OLns4)OLmInitMask();else o3_modal=0;}
}
function OLclearModal(){
if(OLmMaskOn)OLmHideMask();
}

function OLsetModalIframe(o,i,z){
o.id=i;o.src='javascript:false;';o.scrolling='no';var os=o.style;
os.position='absolute';os.zIndex=z;os.filter='Alpha(style=0,opacity=0)';
}

function OLmInitMask(){
OLmRoot=(o3_frame.document.compatMode&&o3_frame.document.compatMode=='BackCompat')?'body':'html';
var doCss=(!OLgetRef('modalMask'))?1:0,zI=(over)?over.style.zIndex-2:998;OLmMask=OLmkLyr('modalMask',o3_frame);
OLmMask.style.zIndex=zI;if(OLie55){if(!OLgetRef('modalIframe')){OLmIframe=o3_frame.document.createElement('iframe');
OLsetModalIframe(OLmIframe,'modalIframe',(zI-1));o3_frame.document.body.appendChild(OLmIframe);}
else OLmIframe.style.zIndex=(zI-1);}var o=OLmMask.style,op=o3_modalopacity;op=(op<=100&&op>0?op:100);
o.backgroundColor=o3_modalcolor;if(doCss){o.display='none';o.top='0px';o.left='0px';o.width='100%';o.height='100%';
o.visibility='visible';if(OLie55){var oi=o3_frame.document.all['modalIframe'].style;oi.display='none';oi.top='0px';
oi.left='0px';oi.width='100%';oi.height='100%';oi.visibility='visible';}}if(OLie4&&!OLieM&&typeof o.filter=='string'){
o.filter='Alpha(opacity='+op+')';if(OLie55)OLmMask.filters.alpha.enabled=1;}else{op=op/100;if(typeof o.opacity!='undefined')
o.opacity=op;else if(typeof o.MozOpacity!='undefined')o.MozOpacity=op;else if(typeof o.KhtmlOpacity!='undefined')
o.KhtmlOpacity=op;}OLmAddEv(window,"resize",OLmHandleMask);OLmShowMask();
}
function OLmShowMask(){
OLmMaskOn=1;if(!OLie4||OLop7){OLmKDH=document.onkeypress?document.onkeypress.toString():null;
document.onkeypress=OLmKeyDownHandler;}else OLmDisableTI();OLmMask.style.display="block";
if(OLie55)OLmIframe.style.display="block";OLmHandleMask();OLmSetMaskSize();
if(!OLmSelectOK)OLmHideSB();
}
function OLmHandleMask(){
if(OLmMaskOn){if(!OLmGotSc){OLmScLeft=parseInt((OLie4&&!OLop7?OLfd(o3_frame).scrollLeft:
o3_frame.pageXOffset),10);OLmScTop=parseInt((OLie4&&!OLop7?OLfd(o3_frame).scrollTop:
o3_frame.pageYOffset),10);OLmGotSc=1;}
var root=o3_frame.document.getElementsByTagName(OLmRoot)[0];if(root.style.overflow!=
'hidden')root.style.overflow='hidden';var scLeft=parseInt((OLie4&&!OLop7?
OLfd(o3_frame).scrollLeft:o3_frame.pageXOffset),10),scTop=parseInt((OLie4&&!OLop7?
OLfd(o3_frame).scrollTop:o3_frame.pageYOffset),10),o=OLmMask.style,oi=(OLie55&&OLmIframe)?
OLmIframe.style:null;o.top=scTop+"px";o.left=scLeft+"px";o.top=scTop+"px";o.left=scLeft+"px";
if(oi){oi.top=scTop+"px";oi.left=scLeft+"px";oi.top=scTop+"px";oi.left=scLeft+"px";}
OLmSetMaskSize();}
}
function OLmSetMaskSize(){
var root=o3_frame.document.getElementsByTagName(OLmRoot)[0],mHt,fullWd=OLmViewportWd(),
fullHt=OLmViewportHt();if(fullHt>root.scrollHeight)mHt=fullHt;else mHt=root.scrollHeight;
OLmMask.style.height=mHt+'px';OLmMask.style.width=root.scrollWidth+'px';if(OLie55&&OLmIframe){
OLmIframe.style.height=mHt+'px';OLmIframe.style.width=root.scrollWidth+'px';}
}
function OLmHideMask(){
OLmMaskOn=0;var root=o3_frame.document.getElementsByTagName(OLmRoot)[0];root.style.overflow=
(OLop7?'auto':'');if(!OLie4||OLop7){document.onkeypress=OLmKDH;OLmKDH=null;}else OLmRestoreTI();
if(!OLmSelectOK)OLmShowSB();OLmRemoveEv(window,"resize",OLmHandleMask);
if(o3_frame.scrollTo&&OLmGotSc){o3_frame.scrollTo(OLmScLeft,OLmScTop);OLmGotSc=0;}
if(OLgetRef('modalMask')&&OLmMask){OLmMask.style.display='none';if(OLie55)
OLmIframe.style.display='none';}OLmEdit=0;
}

function OLmKeyDownHandler(e){
var ev=(e||event),k=ev.keyCode,c=ev.charCode;
if(OLmMaskOn&&!OLmEdit&&(k==9||c==32||(OLgek&&k==13)||(k>=32&&k<=40)))return false;
}

function OLmAddEv(obj,evType,fn){
if(obj.addEventListener){obj.addEventListener(evType,fn,false);return true;}
else if(obj.attachEvent){var r=obj.attachEvent("on"+evType,fn);return r;}else return false;
}
function OLmRemoveEv(obj,evType,fn){
if(obj.removeEventListener){obj.removeEventListener(evType,fn,false);return true;}
else if(obj.detachEvent){var r=obj.detachEvent("on"+evType,fn);return r;}else return false;
}

function OLmViewportWd(){
if(o3_frame.innerWidth!=o3_frame.undefined){return o3_frame.innerWidth;}
if(o3_frame.document.compatMode=='CSS1Compat'){
return o3_frame.document.documentElement.clientWidth;}
if(o3_frame.document.body)return o3_frame.document.body.clientWidth;return o3_frame.undefined;
}
function OLmViewportHt(){
if(o3_frame.innerHeight!=o3_frame.undefined)return o3_frame.innerHeight;
if(o3_frame.document.compatMode=='CSS1Compat')
return o3_frame.document.documentElement.clientHeight;
if(o3_frame.document.body)return o3_frame.document.body.clientHeight;return o3_frame.undefined;
}

function OLmHideSB(){
var s=over.innerHTML;over.innerHTML='';var sel=OLie4?o3_frame.document.all.tags('select'):
o3_frame.document.getElementsByTagName('select');for(i=0;i<sel.length;i++)
sel[i].style.visibility="hidden";over.innerHTML=s;
}
function OLmShowSB(){
var s=over.innerHTML;over.innerHTML='';var sel=OLie4?o3_frame.document.all.tags('select'):
o3_frame.document.getElementsByTagName('select');for(i=0;i<sel.length;i++)
sel[i].style.visibility="visible";over.innerHTML=s;
}

function OLmDisableTI(){
if(OLie4&&!OLop7){var i=0;for(var j=0;j<OLmTT.length;j++){
var tagE=o3_frame.document.getElementsByTagName(OLmTT[j]);for(var k=0;k<tagE.length; k++){
OLmTI[i]=tagE[k].tabIndex;tagE[k].tabIndex="-1";i++;}}}
}
function OLmRestoreTI(){
if(OLie4&&!OLop7){var i=0;for(var j=0;j<OLmTT.length;j++){
var tagE=o3_frame.document.getElementsByTagName(OLmTT[j]);for(var k=0;k<tagE.length;k++){
tagE[k].tabIndex=OLmTI[i];tagE[k].tabEnabled=true;i++;}}}
}

OLregRunTimeFunc(OLloadModal);
OLregCmdLineFunc(OLparseModal);

OLmodalPI=1;
OLloaded=1;
