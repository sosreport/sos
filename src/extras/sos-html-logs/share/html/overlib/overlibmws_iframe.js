/*
 overlibmws_iframe.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   Masks system controls to prevent obscuring of popops for IE v5.5 or higher.
   Initial: October 19, 2003 - Last Revised: April 22, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;

var OLifsP1=null,OLifsSh=null,OLifsP2=null;

// IFRAME SHIM SUPPORT FUNCTIONS
function OLinitIfs(){
if(!OLie55)return;
if((OLovertwoPI)&&over2&&over==over2){
var o=o3_frame.document.all['overIframeOvertwo'];
if(!o||OLifsP2!=o){OLifsP2=null;OLgetIfsP2Ref();}return;}
o=o3_frame.document.all['overIframe'];
if(!o||OLifsP1!=o){OLifsP1=null;OLgetIfsRef();}
if((OLshadowPI)&&o3_shadow){o=o3_frame.document.all['overIframeShadow'];
if(!o||OLifsSh!=o){OLifsSh=null;OLgetIfsShRef();}}
}

function OLsetIfsRef(o,i,z){
o.id=i;o.src='javascript:false;';o.scrolling='no';var os=o.style;os.position='absolute';
os.top='0px';os.left='0px';os.width='1px';os.height='1px';os.visibility='hidden';
os.zIndex=over.style.zIndex-z;os.filter='Alpha(style=0,opacity=0)';
}

function OLgetIfsRef(){
if(OLifsP1||!OLie55)return;
OLifsP1=o3_frame.document.createElement('iframe');
OLsetIfsRef(OLifsP1,'overIframe',2);
o3_frame.document.body.appendChild(OLifsP1);
}

function OLgetIfsShRef(){
if(OLifsSh||!OLie55)return;
OLifsSh=o3_frame.document.createElement('iframe');
OLsetIfsRef(OLifsSh,'overIframeShadow',3);
o3_frame.document.body.appendChild(OLifsSh);
}

function OLgetIfsP2Ref(){
if(OLifsP2||!OLie55)return;
OLifsP2=o3_frame.document.createElement('iframe');
OLsetIfsRef(OLifsP2,'overIframeOvertwo',1);
o3_frame.document.body.appendChild(OLifsP2);
}

function OLsetDispIfs(o,w,h){
var os=o.style;
os.width=w+'px';os.height=h+'px';os.clip='rect(0px '+w+'px '+h+'px 0px)';
o.filters.alpha.enabled=true;
}

function OLdispIfs(){
if(!OLie55)return;
var wd=over.offsetWidth,ht=over.offsetHeight;
if(OLfilterPI&&o3_filter&&o3_filtershadow){wd+=5;ht+=5;}
if((OLovertwoPI)&&over2&&over==over2){
if(!OLifsP2)return;
OLsetDispIfs(OLifsP2,wd,ht);return;}
if(!OLifsP1)return;
OLsetDispIfs(OLifsP1,wd,ht);
if((!OLshadowPI)||!o3_shadow||!OLifsSh)return;
OLsetDispIfs(OLifsSh,wd,ht);
}

function OLshowIfs(){
if(OLifsP1){OLifsP1.style.visibility="visible";
if((OLshadowPI)&&o3_shadow&&OLifsSh)OLifsSh.style.visibility="visible";}
}

function OLhideIfs(o){
if(!OLie55||o!=over)return;
if(OLifsP1)OLifsP1.style.visibility="hidden";
if((OLshadowPI)&&o3_shadow&&OLifsSh)OLifsSh.style.visibility="hidden";
}

function OLrepositionIfs(X,Y){
if(OLie55){if((OLovertwoPI)&&over2&&over==over2){
if(OLifsP2)OLrepositionTo(OLifsP2,X,Y);}
else{if(OLifsP1){OLrepositionTo(OLifsP1,X,Y);if((OLshadowPI)&&o3_shadow&&OLifsSh)
OLrepositionTo(OLifsSh,X+o3_shadowx,Y+o3_shadowy);}}}
}

OLiframePI=1;
OLloaded=1;
