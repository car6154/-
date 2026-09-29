/************************************************************************************/
/* 게시판 상세보기 
/************************************************************************************/


function goView(regid,boardid,boardDiv,flag,type, wtClick_cardbview){
	if (waitTime == 0) {
		alert("로딩중입니다..");
		return;
	}
	else {
		//$("search").action="?regid="+regid+"&method="+type+"&category=004&boardDiv="+boardDiv+"&boardId="+boardid+"&type="+type+"&wtClick_cardbview="+wtClick_cardbview;
		$("search").action="?regid="+regid+"&boardId="+boardid+"&method="+type+"&mnfccd="+$("mnfccd").value+"&mdlcd="+$("mdlcd").value+"&wtClick_cardbview="+wtClick_cardbview;
		$("search").submit();
	}		
	
}


/************************************************************************************/
/* 제원정보로 가기
/************************************************************************************/

function goDimension(mnfccd, mdlcd, caryear){
	location.href = "/db/db_carsinfo.do?method=dimension&mnfccd=" +mnfccd + "&mdlcd=" +mdlcd + "&caryear=" + caryear;  
}

function goDimensionDetail(mnfccd, mdlcd, caryear, dimensiontype){
	location.href = "/db/db_carsinfo.do?method=dimension&dimensiontype=" + dimensiontype + "&mnfccd=" +mnfccd + "&mdlcd=" +mdlcd + "&caryear=" + caryear;  
}

/************************************************************************************/
/* 상세화면 프린트 열기
/************************************************************************************/

function carInfoPrint(mnfcnm,mdlnm,yr,mnfccd,mdlcd,img){
	window.open("/db/db_cars.do?method=detailPrint&mnfcnm="+mnfcnm+"&mdlnm="+mdlnm+"&caryear="+yr+"&mnfccd="+mnfccd+"&mdlcd="+mdlcd+"&type=info&img="+img, "detailPrint", "width=950,height=790,scrollbars=yes");	
}

/************************************************************************************/
/* 메일보내기 
/************************************************************************************/

function sendMail(mnfcnm,mdlnm,yr,mnfccd,mdlcd,img,marketpriceMin,marketprice){
	if($F("isLogin")=='false'){
		if(confirm(("로그인이 필요한 서비스입니다.\n로그인 하시겠습니까?"))){
			location.href=loginURI;	
		}
	}
	if($F("isLogin") == 'true'){
		window.open("/db/db_cars.do?method=sendEmail&mnfcnm="+mnfcnm+"&mdlnm="+mdlnm+"&yr="+yr+"&mnfccd="+mnfccd+"&mdlcd="+mdlcd+"&img="+img+"&marketprice="+marketprice+"&marketpriceMin="+marketpriceMin+"&wtClick_cardbview=035", "detailPrint", "width=570,height=700,scrollbars=yes");		
	}
}
	


/************************************************************************************/
/* 텝 이동 
/************************************************************************************/

function searchTab(type, boardType){
	if($F("mnfccd") == ''){
		alert("제조사를 선택해 주세요");
		return;
	}
	
	if($F("mdlcd") == ''){
		alert("모델을 선택해 주세요");
		return;
	}
	
	if($F("caryear") == ''){
		alert("형식연도를 선택해 주세요");
		return;
	}
	
	if($F("mnfccd") >= '010'){
		$("mdlcd").value = $("mdlcd").value;
		$("groupModel").hide();
	}
	
	if(type == 'cur&wtClick_cardbview=007'){
		$("search").action="/db/db_cars.do?method=marketPrice";
	}else{
		$("search").action="/db/db_cars.do?method=detail&type="+type+"&boardType="+boardType;
	}
	
	$("search").submit();

}

/************************************************************************************/
/* 차량 이미지 스왑 
/************************************************************************************/

function car_swapPicture( crpctpth,idx) {	
	$("carPic").update("<span class='blt'><img src="+crpctpth+" alt='1' class='b' onerror=\"javascript:noImg_B(this);this.style.cursor='';this.state='0';\" /></span>");
			
}



/************************************************************************************/
/* 콤보 박스 셋팅 
/************************************************************************************/


function changeModelGroup(mnfccd) {
	if(mnfccd >= '010'){
		setModelGroup(strModelUrl, modelid, mnfccd, "모델", "");
		$("mdlgroupcd").hide();
		$("mdlcd").show();
		emptyCombo(yearid, "형식연도");
	}else{
		setModelGroup(strModelGroupUrl, modelgroupid, mnfccd, "모델", "");
		emptyCombo(modelid, "세부모델");
		emptyCombo(yearid, "형식연도");
		$("mdlgroupcd").show();
	}
}
function changeModel(mnfccd, mdlgroupcd) {
	
	setModel_New(strModelUrl, modelid, mnfccd, mdlgroupcd, "세부모델", "");
	
	//모델그룹선택시 기본 세부모델선택
	if ($("mdlcd") != null) {
		$("mdlcd").selectedIndex = 1;
		var mdlcd = $("mdlcd").options[$("mdlcd").selectedIndex].value;

		if($("caryear") != null) {
			changeYearJato(mnfccd, mdlcd);
		}
	}	
}

function changeGradeHead(mnfccd, mdlcd) {
	$("mdlcd").style.display = "none";
	$("mdlcd").value = mdlcd;

	if($("caryear") != null) {
		changeYearJato(mnfccd, mdlcd);
	}
}

function changeYearJato(mnfccd,mdlcd) {
	setCarYear(strYrJatoUrl, yearid, mnfccd, mdlcd, "형식연도", "");
	$(yearid).options[1].selected = true;
}

function changeYear(mnfccd,mdlcd) {
	setCarYear(strYrJatoUrl, yearid, mnfccd, mdlcd, "형식연도", "");
	$(yearid).options[1].selected = true;
}

function changeClsDetail(mnfccd, mdlcd, clsheadcd) {
	setGradeDetail(strGradeDetailUrl, gradeDetailid, mnfccd, mdlcd, clsheadcd, "세부등급", "", "");
}

function changeCrash(mnfccd,mdlcd,year) {
	
	setCarCrash(strCrashUrl, organid, mnfccd, mdlcd, year, "기관", "");
}


function changeModelGroupNew(mnfccd, mdlgroupcdId, mdlcdId, yearId) {
	if(mnfccd >= '010'){
		setModelGroup(strModelUrl, mdlcdId, mnfccd, "모델", "");
		$(mdlgroupcdId).hide();
		$(mdlcdId).show();
		emptyCombo(yearId, "형식연도");
	}else{
		setModelGroup(strModelGroupUrl, mdlgroupcdId, mnfccd, "모델", "");
		emptyCombo(mdlcdId, "세부모델");
		emptyCombo(yearId, "형식연도");
		$(mdlgroupcdId).show();
	}
}

function changeModelNew(mnfccd, mdlgroupcd, mdlcdId, yearId) {
	setModel_New(strModelUrl, mdlcdId, mnfccd, mdlgroupcd, "세부모델", "");
	
	//모델그룹선택시 기본 세부모델선택
	if ($(mdlcdId) != null) {
		$(mdlcdId).selectedIndex = 1;
		var mdlcd = $(mdlcdId).options[$(mdlcdId).selectedIndex].value;
		changeYearNew(mnfccd, mdlcd, yearId);
	}	
}

function changeYearNew(mnfccd, mdlcd, yearId) {
	setCarYear(strYrUrl, yearId, mnfccd, mdlcd, "형식연도", "");
	$(yearId).options[1].selected = true;
	changeImage();
}

/************************************************************************************/
/* 카달로그
/************************************************************************************/
	function goCatalog(mnfcd,mdlcd,yr){
		window.open("/dc/dc_catalog.do?method=catalog&company=" + mnfcd + "&model=" + mdlcd + "&yr=" + yr + "&wtClick_carview=019&wtClick_cardbview=036", "catalog", "width=700,height=700,scrollbars=yes");
	}
/************************************************************************************/
/* 게시판 상세보기 
/************************************************************************************/
	function initGnb() {
		var paramCompany = $("paramCompany").value;
		var paramModelGroup = $("paramModelGroup").value;
		var paramModel = $("paramModel").value;
		var paramYr = $("paramYr").value;
				
		// 제조사
		if (paramModel != "") {
			$("mdlcd").show();
		}
		
		setCompany(strCompanyUrl, companyid, "제조사", paramCompany);
		
		// 제조사 값이 있으면 모델 검색
		if (paramCompany >= '010') {
			if (paramCompany != "") {
				if(paramModel == ""){
					paramModel = paramModelGroup;
				}
				setModel(strModelUrl, modelid, paramCompany, "모델", paramModel)
				$("mdlgroupcd").hide();
				
			}
		}else{
			$("mdlgroupcd").show();
			if (paramCompany != "") {
				setModelGroup(strModelGroupUrl, modelgroupid, paramCompany, "모델", paramModelGroup);
				if (paramModelGroup != "") {
					setModel_New(strModelUrl, modelid, paramCompany, paramModelGroup, "세부모델", paramModel);
				}
			}
		
		}
		if (paramCompany != "" && paramModel != "") {
			setCarYear(strYrJatoUrl, yearid, paramCompany, paramModel, "형식연도", paramYr);
		}	

		waitTime = 1;
	}


/************************************************************************************/
/* 게시판 상세보기 
/************************************************************************************/

// 모델비교 이동
// - type : 1, 2
//    1일때 : 제조사, 모델, 형식연도, 등급
//    2일때 : 제조사, 모델, 형식연도, 등급객체(히든), 세부등급
function moveModelCompare(type, urlType, mnfccd, mdlcd, year, clsheadcd, clsdetailcd) {
	//alert("moveModelCompare()");
	if(type == "1") {
		if(clsheadcd == "" || clsheadcd == undefined) clsheadcd = "";
	}else if(type == "2") {
		clsheadcd = $(clsheadcd).value;
	}
	if(clsdetailcd == "" || clsdetailcd == undefined) clsdetailcd = "";
	
	// 이동URL 선택 
	//   - urlType (1:주요제원, 2:성능/차체, 3:외관/내장, 4:안전/편의)
	var url = "/db/db_compare.do?method=compare";
	if(urlType == "1") {
		url = url;
	}else if(urlType == "2") {
		url = url + "&dimensiontype=performance";
	}else if(urlType == "3") {
		url = url + "&dimensiontype=outinner";
	}else if(urlType == "4") {
		url = url + "&dimensiontype=safety";
	}
	url = url + "&paramType=1&car_mnfccd="+mnfccd+"&car_mdlcd="+mdlcd+"&car_year="+year+"&car_clsheadcd="+clsheadcd+"&car_clsdetailcd="+clsdetailcd;
	window.location.href=url;		
}

function ncheck(num){
	var chkflag=true;
	for(var i =0;i<num.length;i++){
		c=num.charAt(i);
		if(!(c>='0' && c<='9')) {
	    	chkflag=false;
			//break;
      	}
	}
  	return chkflag;
}


function numchk(v,n){
	v=v.replace("-","");
	if(!ncheck(v)){		
		alert('숫자만 입력하실 수 있습니다.');
		var temp=eval($(n));
	
		temp.value='';
		temp.focus();
	}
	if (v.length == 6) {			
		var temp=eval($(n));		
		temp.value = v + '-';
	}
}


//차량이미지 리스트 이미지
function dbNoImg_S(obj){
	obj.src="/images/db/img_noImg_S.gif";
}

function dbNoImg_M(obj){
	obj.src="/images/db/img_noImg_M.gif";
}

function dbNoImg_L(obj){
	obj.src="/images/db/img_noImg_L.gif";
}


//차량이미지 리스트 이미지
function dbNoImg_main_S(obj, mnfccd, mdlcd, yr){
	obj.src=$("imgUrl").value + "/carsdata/cars/cm_cardb/file/" + mnfccd + "_" + mdlcd + "_" + yr + "_s.jpg";
}