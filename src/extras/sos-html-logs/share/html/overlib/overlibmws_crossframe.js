/*
 overlibmws_crossframe.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For support of FRAME.
   Initial: August 3, 2003 - Last Revised: January 1, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
OLregCmds('frame');

function OLparseCrossframe(pf,i,ar){
var k=i,v;
if(k<ar.length){
if(ar[k]==FRAME){v=ar[++k];if(pf=='ol_')ol_frame=v;else OLoptFRAME(v);return k;}}
return -1;
}

function OLgetFrameRef(thisFrame,ofrm){
var i,v,retVal='';for(i=0;i<thisFrame.length;i++){if((((thisFrame[i].length>0)))&&(((OLns4))||
((OLie4)&&(v=thisFrame[i].document.all.tags('iframe'))!=null&&v.length==0)||
((OLns6)&&(v=thisFrame[i].document.getElementsByTagName('iframe'))!=null&&v.length==0))){
retVal=OLgetFrameRef(thisFrame[i],ofrm);if(retVal=='')continue;}
else if(thisFrame[i]!=ofrm)continue;retVal='['+i+']'+retVal;break;}
return retVal;
}

function OLoptFRAME(frm){
o3_frame=OLmkLyr('overDiv',frm)?frm:self;if(o3_frame!=self){
var l,tFrm=OLgetFrameRef(top.frames,o3_frame),sFrm=OLgetFrameRef(top.frames,ol_frame);
if(sFrm.length==tFrm.length) {l=tFrm.lastIndexOf('[');if(l){
while(sFrm.substring(0,l)!=tFrm.substring(0,l))l=tFrm.lastIndexOf('[',l-1);
tFrm=tFrm.substr(l);sFrm=sFrm.substr(l);}}var i,k,cnt=0,p='',str=tFrm;
while((k=str.lastIndexOf('['))!= -1){cnt++;str=str.substring(0,k);}
for(i=0;i<cnt;i++)p=p+'parent.';OLfnRef=p+'frames'+sFrm+'.';}
}

OLregCmdLineFunc(OLparseCrossframe);

OLcrossframePI=1;
OLloaded=1;
