/*
 overlibmws_bubble.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For support of the BUBBLE feature.
   Initial: July 26, 2003 - Last Revised: January 1, 2007 
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
var OLbubbleCmds='bubble,bubbletype,adjbubble';
OLregCmds(OLbubbleCmds);

// DEFAULT CONFIGURATION
if(OLud('bubble'))var ol_bubble=0;
if(OLud('bubbletype'))var ol_bubbletype='';
if(OLud('adjbubble'))var ol_adjbubble=0;
// END CONFIGURATION

if(typeof OLbubbleImages=='undefined')
var OLbubbleImages='flower,oval,square,pushpin,quotation,roundcorners';
if(typeof OLbubbleImageDir=='undefined')var OLbubbleImageDir='./';
OLregisterImages('flower,oval,square,pushpin,quotation,roundcorners',OLbubbleImageDir);
var OLimgWidth=[250,330,144,202,200];
var OLimgHeight=[150,160,190,221,66];
var OLcontentWidth=[200,250,130,184,190];
var OLcontentHeight=[80,85,150,176,46];
var OLpadLeft=[30,40,7,9,5];
var OLpadTop=[25,48,10,34,4];
var OLarwTipX=[180,50,51,9,19];
var OLarwTipY=[148,5,180,221,64];
var OLbI,OLbContentWd=OLcontentWidth;

var o3_bubble=0,o3_bubbletype='',o3_adjbubble=0,OLbubbleHt=0;

function OLloadBubble(){
OLload(OLbubbleCmds);OLbubbleHt=0;
}

function OLparseBubble(pf,i,ar){
var k=i,t=OLtoggle;
if(k<ar.length){
if(Math.abs(ar[k])==BUBBLE){t(ar[k],pf+'bubble');return k;}
if(ar[k]==BUBBLETYPE){OLparQuo(ar[++k],pf+'bubbletype');return k;}
if(Math.abs(ar[k])==ADJBUBBLE){t(ar[k],pf+'adjbubble');return k;}}
return -1;
}

function OLchkForBubbleEffect() {
if(o3_bubble){o3_bubbletype=(o3_bubbletype)?o3_bubbletype:'flower';
for(var i=0;i<OLbTypes.length;i++){if(OLbTypes[i]==o3_bubbletype){OLbI=i;break;}}
// disable inappropriate parameters
o3_bgcolor=o3_fgcolor='';
o3_border=o3_base=0;
o3_fgbackground=o3_bgbackground=o3_cgbackground=o3_background='';
o3_cap='';
if(o3_sticky)o3_noclose=1;
o3_fullhtml=0;
if(OLshadowPI)o3_shadow=0;
if(o3_bubbletype!='roundcorners'){
o3_width=OLbContentWd[OLbI];
o3_hpos=RIGHT;
o3_vpos=BELOW;
o3_vauto=0;
o3_hauto=0;
o3_wrap=0;
o3_nojusty=1;}}
return true;
}

function OLregisterImages(imgStr,path) {
if(typeof imgStr!='string')return;
path=(path&&typeof path=='string')?path:'.';
if(path.charAt(path.length-1)=='/')path=path.substring(0,path.length-1);
if(typeof OLbTypes=='undefined')OLbTypes=imgStr.split(',');
if(typeof OLbubbleImg=='undefined'){
OLbubbleImg=new Array();
for(var i=0;i<OLbTypes.length;i++){
if(OLbubbleImages.indexOf(OLbTypes[i])<0)continue;
if(OLbTypes[i]=='roundcorners'){
OLbubbleImg[i]=new Array();
var o=OLbubbleImg[i];
o[0]=new Image();o[0].src=path+'/cornerTL.gif';
o[1]=new Image();o[1].src=path+'/edgeT.gif';
o[2]=new Image();o[2].src=path+'/cornerTR.gif';
o[3]=new Image();o[3].src=path+'/edgeL.gif';
o[4]=new Image();o[4].src=path+'/edgeR.gif';
o[5]=new Image();o[5].src=path+'/cornerBL.gif';
o[6]=new Image();o[6].src=path+'/edgeB.gif';
o[7]=new Image();o[7].src=path+'/cornerBR.gif';
}else{
OLbubbleImg[i]=new Image();OLbubbleImg[i].src=path+'/'+OLbTypes[i]+'.gif';}}}
}

function OLgenerateBubble(content) {
if(!o3_bubble)return;
if(o3_bubbletype=='roundcorners')return OLdoRoundCorners(content);
var ar,X,Y,fc=1.0,txt,sY,bHtDiff,bPadDiff=0,bLobj,bCobj;
var bTopPad=OLpadTop,bLeftPad=OLpadLeft;
var bContentHt=OLcontentHeight,bHt=OLimgHeight;
var bWd=OLimgWidth,bArwTipX=OLarwTipX,bArwTipY=OLarwTipY;
bHtDiff=fc*bContentHt[OLbI]-(OLns4?over.clip.height:over.offsetHeight);
if(o3_adjbubble){
fc=OLresizeBubble(bHtDiff,0.5,fc);
ar=OLgetHeightDiff(fc);
bHtDiff=ar[0];
content=ar[1];}
if(bHtDiff>0)bPadDiff=(bHtDiff<2)?0:parseInt(0.5*bHtDiff);
Y=(bHtDiff<0)?fc*bTopPad[OLbI]:fc*bTopPad[OLbI]+bPadDiff;
X=fc*bLeftPad[OLbI];
Y=Math.round(Y);
X=Math.round(X);
o3_width=fc*bWd[OLbI];
OLbubbleHt=fc*bHt[OLbI];
txt='<img src="'+OLbubbleImg[OLbI].src+'" width="'+o3_width+'" height="'
+(bHtDiff<0?OLbubbleHt-bHtDiff:OLbubbleHt)+'" />'+(OLns4?'<div id="bContent">':
'<div id="bContent" style="position:absolute; top:'+Y+'px; left:'+X+'px; width:'
+fc*OLbContentWd[OLbI]+'px; z-index:1;">')+content+'</div>';
OLlayerWrite(txt);
if(OLns4){
bCobj=over.document.layers['bContent'];
if(typeof bCobj=='undefined')return;
bCobj.top=Y;
bCobj.left=X;
bCobj.clip.width=fc*OLbContentWd[OLbI];
bCobj.zIndex=1;}
if(fc*bArwTipY[OLbI]<0.5*fc*bHt[OLbI])sY=fc*bArwTipY[OLbI]; 
else sY= -(fc*bHt[OLbI]+20);
o3_offsetx -=fc*bArwTipX[OLbI];
o3_offsety +=sY;
}

function OLdoRoundCorners(content) {
var txt,wd,ht,o=OLbubbleImg[OLbI];
wd=(OLns4)?over.clip.width:over.offsetWidth;
ht=(OLns4)?over.clip.height:over.offsetHeight;
txt='<table cellpadding="0" cellspacing="0" border="0">'
+'<tr><td align="right" valign="bottom"><img src="'+o[0].src+'" width="14" height="14"'
+(OLns6?' style="display:block;"':'')+' /></td><td valign="bottom"><img src="'+o[1].src
+'" height="14" width="'+wd+'"'+(OLns6?' style="display:block;"':'')
+' /></td><td align="left" valign="bottom"><img src="'+o[2].src+'" width="14" height="14"'
+(OLns6?' style="display:block;"':'')+' /></td></tr>'
+'<tr><td align="right"><img src="'+o[3].src+'" width="14" height="'+ht+'"'
+(OLns6?' style="display:block;"':'')+' /></td><td bgcolor="#ffffcc">'+content
+'</td><td align="left"><img src="'+o[4].src+'" width="14" height="'+ht+'"'
+(OLns6?' style="display:block;"':'')+ '/></td></tr>'+'<tr><td align="right" valign="top">'
+'<img src="'+o[5].src+'" width="14" height="14" /></td><td valign="top"><img src="'+o[6].src
+'" height="14" width="'+wd+'" /></td><td align="left" valign="top"><img src="'+o[7].src
+'" width="14" height="14" /></td></tr></table>';
OLlayerWrite(txt);
o3_width=wd+28;
OLbubbleHt=ht+28;
}

function OLresizeBubble(h1,dF,fold){
var df,h2,fnew,alpha,cnt=0;
while(cnt<2){
df= -OLsignOf(h1)*dF;
fnew=fold+df;
h2=OLgetHeightDiff(fnew)[0];
if(Math.abs(h2)<11)break;
if(OLsignOf(h1)!=OLsignOf(h2)){
alpha=Math.abs(h1)/(Math.abs(h1)+Math.abs(h2));
if(h1<0)fnew=alpha*fnew+(1.0-alpha)*fold;
else fnew=(1.0-alpha)*fnew+alpha*fold;
}else{
alpha=Math.abs(h1)/(Math.abs(h2)-Math.abs(h1));
if(h1<0)fnew=(1.0+alpha)*fold-alpha*fnew;
else fnew=(1.0+alpha)*fnew-alpha*fold;}
fold=fnew;
h1=h2;
dF*=0.5;
cnt++;}
return fnew;
}

function OLgetHeightDiff(f){
var lyrhtml;
o3_width=f*OLcontentWidth[OLbI];
lyrhtml=OLcontentSimple(o3_text);
OLlayerWrite(lyrhtml)
return [f*OLcontentHeight[OLbI]-((OLns4)?over.clip.height:over.offsetHeight),lyrhtml];
}

function OLsignOf(x){
return (x<0)? -1:1;
}

OLregRunTimeFunc(OLloadBubble);
OLregCmdLineFunc(OLparseBubble);

if(OLns4)
document.write(
'<style type="text/css">\n<!--\n#bContent{position:absolute;left:0px;top:0px;width:1024}\n'
+'-->\n<'+'\/style>');
OLbubblePI=1;
OLloaded=1;
