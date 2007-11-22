/*
 overlibmws_exclusive.js plug-in module - Copyright Foteos Macrides 2003-2007. All rights reserved.
   For support of the EXCLUSIVE feature.
   Initial: November 7, 2003 - Last Revised: January 1, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
var OLexclusiveCmds='exclusive,exclusivestatus,exclusiveoverride';
OLregCmds(OLexclusiveCmds);

// DEFAULT CONFIGURATION
if(OLud('exclusive'))var ol_exclusive=0;
if(OLud('exclusivestatus'))var ol_exclusivestatus='Please act on or close the open popup.';
if(OLud('exclusiveoverride'))var ol_exclusiveoverride=0;
// END CONFIGURATION

var o3_exclusive=0,o3_exclusivestatus='',o3_exclusiveoverride=0;

function OLloadExclusive(){
OLload(OLexclusiveCmds);
}

function OLparseExclusive(pf,i,ar){
var k=i,t=OLtoggle;
if(k<ar.length){
if(Math.abs(ar[k])==EXCLUSIVE){t(ar[k],pf+'exclusive');return k;}
if(ar[k]==EXCLUSIVESTATUS){OLparQuo(ar[++k],pf+'exclusivestatus');return k;}
if(Math.abs(ar[k])==EXCLUSIVEOVERRIDE){t(ar[k],pf+'exclusiveoverride');return k;}}
return -1;
}

function OLisExclusive(args){
if((args!=null)&&OLhasOverRide(args))o3_exclusiveoverride=(ol_exclusiveoverride==0)?1:0;
else o3_exclusiveoverride=ol_exclusiveoverride;
var rtnVal=(o3_exclusive&&!o3_exclusiveoverride&&OLshowingsticky&&
over==OLgetRefById('overDiv'));
if(rtnVal)self.status=o3_exclusivestatus;
return rtnVal;
}

function OLhasOverRide(args){
var rtnFlag=0;
for(var i=0;i<args.length;i++){
if(typeof args[i]=='number'&&args[i]==EXCLUSIVEOVERRIDE){
rtnFlag=1;break;}}
return rtnFlag;
}

OLregRunTimeFunc(OLloadExclusive);
OLregCmdLineFunc(OLparseExclusive);

OLexclusivePI=1;
OLloaded=1;
