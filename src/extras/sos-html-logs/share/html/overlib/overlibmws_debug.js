/*
 overlibmws_debug.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For support of the OLshowProperties() debugging function.
   Initial: July 26, 2003 - Last Revised: January 1, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
var OLzIndex;
OLregCmds('allowdebug');

// DEFAULT CONFIGURATION
if(OLud('allowdebug'))var ol_allowdebug='';
// END CONFIGURATION

var o3_allowdebug='';

function OLloadDebug(){
OLload('allowdebug');
}

function OLparseDebug(pf,i,ar){
var k=i;
if(ar[k]==ALLOWDEBUG){
if(k<(ar.length-1)&&typeof ar[k+1]=='string')OLparQuo(ar[++k],pf+'allowdebug');return k;}
return -1;
}

function OLshowProperties(){
var ar=arguments,sho,shoS,vis,lvl=0,istrt=0,theDiv='showProps',txt='',
fac='Verdana,Arial,Helvetica',siz=(OLns4?'1':'67%'),
fon='><font color="#000000" face="'+fac+'" size="'+siz,
stl=' style="font-family:'+fac+';font-size:'+siz+';',
sty=stl+'color:#000000;',clo=(OLns4?'</font>':'');
if(ar.length==0)return;
if(ar.length%2&&typeof ar[0]=='string'){istrt=1;theDiv=ar[0];}
if(!(sho=OLmkLyr(theDiv,self)))return;
shoS=(OLns4)?sho:sho.style;
lvl=OLgetLayerLevel(theDiv);
if(typeof sho.position=='undefined'){
sho.position=new OLpageLocDebug(10+lvl*20,10,1);
if(typeof OLzIndex=='undefined')OLzIndex=OLgetDivZindex('overDiv',self);
shoS.zIndex=OLzIndex+1+lvl;}
txt='<table cellpadding="1" cellspacing="0" border="0" bgcolor="#000000"><tr><td>'
+'<table cellpadding="5" border="0" cellspacing="0" bgcolor="#ffffcc">'
+'<tr><td><strong><a href="javascript:OLmoveToBack(\''+theDiv+'\');" title="Move to back"'
+(OLns4?fon:stl)+'">'+theDiv+clo
+'</a></strong></td><td align="right"><strong><a href="javascript:OLcloseLayer(\''+theDiv
+'\');" title="Close Layer"'+(OLns4?fon:stl
+'background-color:#cccccc;border:1px #333369 outset;padding:0px;')+'">X'+clo
+'</a></strong></td></tr><tr><td'+(OLns4?fon:sty)+'">'+'<strong><em>Item</em></strong>'
+clo+'</td><td'+(OLns4?fon:sty)+'">'+'<strong><em>Value</em></strong>'+clo+'</td></tr>';
for(var i=istrt;i<ar.length-1;i++)
txt+='<tr><td align="right"'+(OLns4?fon:sty)+'">'+'<strong>'+ar[i]+':&nbsp;</strong>'
+clo+'</td><td'+(OLns4?fon:sty)+'">'+ar[++i]+clo+'</td></tr>';
txt+='</table></td></tr></table>';
if(OLns4){sho.document.open();sho.document.write(txt);sho.document.close();
}else{if(OLie4&&OLieM)sho.innerHTML='';sho.innerHTML=txt;}
OLshowAllVisibleLayers();
}

function OLgetLayerLevel(lyr){
var i=0;
if(typeof document.popups=='undefined'){document.popups=new Array(lyr);
}else{var l=document.popups;for(i=0;i<l.length;i++)if(lyr==l[i])break;
if(i==l.length)l[l.length++]=lyr;}
return i;
}

function OLgetDivZindex(id,f){
if(!id)id='overDiv';if(!f)f=o3_frame;
var o=OLgetRefById(id,f.document);
if(o){o=OLns4?o:o.style;return o.zIndex;}
else return 1000;
}

function OLsetDebugCanShow(){
if(o3_allowdebug!=''){
var i,lyr,pLyr=o3_allowdebug.replace(/[ ]/ig,'').split(',');
for(i=0;i<pLyr.length;i++){lyr=OLgetRefById(pLyr[i],self.document);
if(lyr&&typeof lyr.position!='undefined')lyr.position.canShow=1;}}
}

function OLpageLocDebug(x,y,canShow){
this.x=x;this.y=y;this.canShow=(canShow==null)?0:canShow;
}

function OLshowAllVisibleLayers(){
var i,lyr,o,l=document.popups;
for(i=0;i<l.length;i++){if((lyr=OLgetRefById(l[i],self.document))&&lyr.position.canShow){
o=OLns4?lyr:lyr.style;OLpositionLayer(o,lyr.position.x,lyr.position.y);o.visibility='visible';}}
}

function OLpositionLayer(o,x,y){
o.left=x+(OLie4?OLfd(self).scrollLeft:self.pageXOffset)+(OLns4?0:'px');
o.top=y+(OLie4?OLfd(self).scrollTop:self.pageYOffset)+(OLns4?0:'px');
}

function OLcloseLayer(id){
var lyr=OLgetRefById(id,self.document);
if(lyr){lyr.position.canShow=0;lyr=OLns4?lyr:lyr.style;lyr.visibility='hidden';}
}

function OLmoveToBack(layer){
var l=document.popups,lyr,o,i,x=10,dx=20,z=OLzIndex+1;if(l.length==1)return;
if(lyr=OLgetRefById(layer,self.document)){lyr.position.x=x;o=OLns4?lyr:lyr.style;o.zIndex=z;
for(i=0;i<l.length;i++){if(layer==l[i])continue;
if(!(lyr=OLgetRefById(l[i],self.document))||lyr.position.canShow==0)continue;
o=OLns4?lyr:lyr.style;o.zIndex+=1;lyr.position.x+=dx;}OLshowAllVisibleLayers();}
}

OLregRunTimeFunc(OLloadDebug);
OLregCmdLineFunc(OLparseDebug);

OLdebugPI=1;
OLloaded=1;
