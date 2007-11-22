/*
 overlibmws_hide.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For hiding elements.
   Initial: November 13, 2003 - Last Revised: March 10, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
var OLhideCmds='hideselectboxes,hidebyid,hidebyidall,hidebyidns4';
OLregCmds(OLhideCmds);

// DEFAULT CONFIGURATION
if(OLud('hideselectboxes'))var ol_hideselectboxes=0;
if(OLud('hidebyid'))var ol_hidebyid='';
if(OLud('hidebyidall'))var ol_hidebyidall='';
if(OLud('hidebyidns4'))var ol_hidebyidns4='';
// END CONFIGURATION

var o3_hideselectboxes=0,o3_hidebyid='',o3_hidebyidall='',o3_hidebyidns4='',
OLselectOK=(OLie7||OLop7||OLgek>=20030624)?1:0;

function OLloadHide(){
OLload(OLhideCmds);
}

function OLparseHide(pf,i,ar){
var k=i,q=OLparQuo;
if(k<ar.length){
if(Math.abs(ar[k])==HIDESELECTBOXES){OLtoggle(ar[k],pf+'hideselectboxes');return k;}
if(ar[k]==HIDEBYID){q(ar[++k],pf+'hidebyid');return k;}
if(ar[k]==HIDEBYIDALL){q(ar[++k],pf+'hidebyidall');return k;}
if(ar[k]==HIDEBYIDNS4){q(ar[++k],pf+'hidebyidns4');return k;}}
return -1;
}

function OLchkHide(hide){
if(OLiframePI&&OLie55)return;if(OLmodalPI&&o3_modal)o3_hideselectboxes=0;var id,o,i;
if(o3_hidebyid&&typeof o3_hidebyid=='string'&&!(o3_hideselectboxes&&OLns6)&&!OLop7&&!OLns4){
id=o3_hidebyid.replace(/[ ]/ig,'').split(',');for(i=0;i<id.length;i++){
o=(OLie4?o3_frame.document.all[id[i]]:OLns6?o3_frame.document.getElementById(id[i]):null);
if(o)o.style.visibility=(hide?'hidden':'visible');}}
if(o3_hidebyidall&&typeof o3_hidebyidall=='string'){
id=o3_hidebyidall.replace(/[ ]/ig,'').split(',');for(i=0;i<id.length;i++){
o=OLgetRefById(id[i]);if(o){o=(OLns4)?o:o.style;
o.visibility=(hide?'hidden':'visible');}}}
if(o3_hidebyidns4&&OLns4&&typeof o3_hidebyidns4=='string'){
id=o3_hidebyidns4.replace(/[ ]/ig,'').split(',');for(i=0;i<id.length;i++){
o=eval('o3_frame.document.'+id[i]);if(o)o.visibility=(hide?'hidden':'visible');}}
}

function OLselectBoxes(hide,all){
if((OLiframePI&&OLie55)||OLselectOK||OLns4)return;var sel=OLie4?
o3_frame.document.all.tags('select'):o3_frame.document.getElementsByTagName('select'),
px=over.offsetLeft,py=over.offsetTop,pw=over.offsetWidth,ph=over.offsetHeight,bx=px,by=py,
bw=pw,bh=ph,sx,sy,sw,sh,i,sp,si;if((OLshadowPI)&&bkdrop&&o3_shadow){bx=bkdrop.offsetLeft;
by=bkdrop.offsetTop;bw=bkdrop.offsetWidth;bh=bkdrop.offsetHeight;}for(i=0;i<sel.length;i++){
sx=0;sy=0;si=0;if(sel[i].offsetParent){sp=sel[i];while(sp.offsetParent&&
sp.offsetParent.tagName.toLowerCase()!='body'){if(sp.offsetParent.id=='overDiv'||
sp.offsetParent.id=='overDiv2')si=1;sp=sp.offsetParent;sx+=sp.offsetLeft;sy+=sp.offsetTop;}
sx+=sel[i].offsetLeft;sy+=sel[i].offsetTop;sw=sel[i].offsetWidth;sh=sel[i].offsetHeight;
if(si||(!OLie4&&sel[i].size<2))continue;else if(hide){if((px+pw>sx&&px<sx+sw&&py+ph>sy&&
py<sy+sh)||(bx+bw>sx&&bx<sx+sw&&by+bh>sy&&by<sy+sh)){if(sel[i].style.visibility!="hidden")
sel[i].style.visibility="hidden";}}else{if(all||(!(OLovertwoPI&&over==over2)&&(px+pw<sx||
px>sx+sw||py+ph<sy||py>sy+sh)&&(bx+bw<sx||bx>sx+sw||by+bh<sy||by>sy+sh))){
if(sel[i].style.visibility!="visible")sel[i].style.visibility="visible";}}}}
}

function OLhideUtil(a1,a2,a3,a4,a5,a6){
if(a4==null){OLchkHide(a1);if(o3_hideselectboxes)OLselectBoxes(a2,a3);}else{OLchkHide(a1);
OLchkHide(a2);if(o3_hideselectboxes){OLselectBoxes(a3,a4);OLselectBoxes(a5,a6);}}
}

OLregRunTimeFunc(OLloadHide);
OLregCmdLineFunc(OLparseHide);

OLhidePI=1;
OLloaded=1;
