	/***************************************************************************************/
	/* 차량디비와 연동된 변속기, 연료, 배기량 초기화
	/***************************************************************************************/
	function ititCarDbCombo(){
		setComboCarcd(strCarCdUrl, "trans", "001", "name", "선택", "");
		setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", ""); //연료
		$('dsp').value = "";
	}
	
	/***************************************************************************************/
	/* Select 박스 컨트롤 함수
	/***************************************************************************************/
	// 콤보박스 데이터 조회
	function setCombo(strComboUrl, comboid, initvalue) { 
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false, 
				onSuccess: function(responseHttpObj) {
					displayCombo(responseHttpObj, comboid, initvalue);
				}, 
				onFailure: function() {
	            	displayError( comboid, initvalue);
	            }
			}
		)
	}
	// 콤보박스 데이터 조회
	function setComboSelected(strComboUrl, comboid, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				encoding: "euc-kr",
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError( comboid, initvalue);
	            }
			}
		)
	}
	
	// 콤보박스 데이터 조회
	function setComboCarcd(strComboUrl, comboid, mjrcd, valueType, initvalue, selectedValue) {		
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mjrcd":mjrcd, "valueType":valueType, "selectedValue":selectedValue},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError( comboid, initvalue);
	            }
			}
		)
	}	
	
	// 변속기 차량디비 연동
	function setComboCarDbTrns(strComboUrl, comboid, mjrcd, valueType, initvalue, mnfccd, mdlcd, clsheadcd, clsdetailcd, year) {
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"valueType":valueType, "mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "clsdetailcd":clsdetailcd, "year":year},
					onSuccess: function(responseHttpObj) {
						displayComboSelected(responseHttpObj, comboid, initvalue, "");
					}, 
					onFailure: function() {
						displayError( comboid, initvalue);
					}
				}
		)
	}
	
	// 변속기 차량디비 존재여부
	// (수입차개선) 세부모델이 존재하지않는경우 체크 : 20120615 JSI
	function getComboCarDbTrnsCheck(strComboUrl, valueType, mnfccd, mdlcd, clsheadcd, clsdetailcd, year, groupchk, mdlgroupcd) {
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"valueType":valueType, "mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "clsdetailcd":clsdetailcd, "year":year, 
								"groupchk":groupchk, "mdlgroupcd":mdlgroupcd},
					onSuccess: function(responseHttpObj) {
						var returnData = responseHttpObj.responseText.trim();
						var data = eval("(" + returnData  + ")");

						if(data.length == 1){
							//setComboCarDbTrns(strCarCdUrl, "trans", "001", "cardbtrns", "선택", mnfccd, mdlcd, clsheadcd, clsdetailcd, year);
							setComboCarcd(strCarCdUrl, "trans", "001", "name", "선택", data[0].name);
						}else{
							setComboCarcd(strCarCdUrl, "trans", "001", "name", "선택", "");
						}
					}, 
					onFailure: function() {
						return false;
					}
				}
		)
	}
	
		
	// 연료 차량디비 연동
	// (수입차개선) 세부모델이 존재하지않는경우 체크 : 20120615 JSI
	function setComboCarDbFuel(strComboUrl, valueType, mnfccd, mdlcd, clsheadcd, clsdetailcd, year, groupchk, mdlgroupcd) {
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"valueType":valueType, "mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "clsdetailcd":clsdetailcd, "year":year},
					onSuccess: function(responseHttpObj) {
						//연료가 두가지 이상 리턴될시 false
						//한가지만 리턴되면 그 값을 리턴
						var returnData = responseHttpObj.responseText.trim();
						var data = eval("(" + returnData  + ")");
						if(data.length == 1){
							setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", data[0].type); //연료							
						}else{
							setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", ""); //연료
						}
					}, 
					onFailure: function() {
						setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", ""); //연료
					}
				}
		)
	}
	
	//연료정보 등급테이블에서 호출(등급선택시)
	function setFuelComboFromClass(strComboUrl, valueType, mnfccd, mdlcd, clsheadcd) {
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"valueType":valueType, "mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd},
					onSuccess: function(responseHttpObj) {
						//연료가 두가지 이상 리턴될시 false
						//한가지만 리턴되면 그 값을 리턴
						var returnData = responseHttpObj.responseText.trim();
						var data = eval("(" + returnData  + ")");
						
						if(data.length == 1){
							setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", data[0].type); //연료
							
						}else{
							setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", ""); //연료
						}
					}, 
					onFailure: function() {
						setComboCarcd(strCarCdUrl, "fuel", "017", "code", "선택", ""); //연료
					}
				}
		)
	}
	
	// 배기량 차량디비 연동
	// (수입차개선) 세부모델이 존재하지않는경우 체크 : 20120615 JSI
	function setComboCarDbDsp(strComboUrl, valueType, mnfccd, mdlcd, clsheadcd, clsdetailcd, year, groupchk, mdlgroupcd) {
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"valueType":valueType, "mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "clsdetailcd":clsdetailcd, "year":year,
								"groupchk":groupchk, "mdlgroupcd":mdlgroupcd},
					onSuccess: function(responseHttpObj) {
						//배기량이 두가지 이상 리턴될시 false
						//한가지만 리턴되면 그 값을 리턴
						var returnData = responseHttpObj.responseText.trim();
						var data = eval("(" + returnData  + ")");
						
						if(data.length == 1){
							$('dsp').value = data[0].name;
						}else{
							$('dsp').value = "";
						}
					}, 
					onFailure: function() {
						$('dsp').value = "";
					}
				}
		)
	}
	
	function returnValue(responseHttpObj){
		var returnData = responseHttpObj.responseText.trim();
		var data = eval("(" + returnData  + ")");
		
		if(data.length == 1){
			return data[0].name;
		}else{
			return false;
		}
	}

	
	
	
	// 콤보박스 출력
	function displayCombo(responseHttpObj, comboid, initvalue) {
		var returnData = responseHttpObj.responseText.trim();
		var data = eval("(" + returnData  + ")");
		
		removeOptions($(comboid));
		
		addOption($(comboid), "", initvalue);
		
		for (var i = 0 ; i < data.length ; i++) {
			addOption($(comboid), data[i].abbreviation, data[i].label);
		}
	}
	
	// 콤보박스 출력
	var colorArray = new Array();	// 색상 콤보 박스는 색상값(expl)을 배열로 갖도록 한다.
	function displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue, comboType) {


		var returnData = responseHttpObj.responseText.trim();
		var data = eval("(" + returnData  + ")");

		removeOptions($(comboid));

		addOption($(comboid), "", initvalue);


		for (var i = 0 ; i < data.length ; i++) {
			/* 세부등급 그룹핑 레이블 처리 */
			if ( data[i].group_nm != null && ( comboid == 'gradeDetail' || comboid == 'gradedetail'  || comboid == 'clsdetailcd' || comboid == '"mdl_clsdetailcd' )) {
				if ( data[i].group_nm != null && data[i].group_nm != "" ) {
					var groupnm = "(" + data[i].group_nm + ")";
					data[i].label = groupnm + data[i].label;
				}
			}
			addOption($(comboid), data[i].abbreviation, data[i].label);			

			// 색상 코드인 경우는 아래가 같이 해결 할것.
			if (comboid== "color" && data[i].type == "003") {
				colorArray[data[i].abbreviation] = data[i].expl;
			}
		}

		if (selectedValue != "") {
			$(comboid).value = selectedValue;
		}

		if(data.length < 1 && initvalue == "적재용량") {
			removeOptions($(comboid));
			addOption($(comboid), "", initvalue);
			addOption($(comboid), "000", "없 음");
		}

		if(data.length < 1 && initvalue == "등급") {
		    removeOptions($(comboid));
			addOption($(comboid), "000", "없 음");
		}

		if($(comboid).disable()) $(comboid).enable();
		var str_comboid = ""+comboid;
		// 세부등급인 경우는 select 박스의 활성화를 변경한다. 시군구 세종시의경우 구군이없어서 추가
		if (comboid == "gradeDetail" || comboid == "clsdetailcd" || comboid == "mdl_clsdetailcd" || (str_comboid.indexOf("cntcsgng")>=0)) {
			if (data.length <= 0) {
				$(comboid).disable();
				//등급까지 있는경우 여기서 차량디비 데이터 조회
				/*getComboCarDbTrnsCheck(strCarCdUrl, "cardbtrns", $("company").value, $("model").value, $("gradeHead").value, $("gradeDetail").value);
				setComboCarDbFuel(strCarCdUrl, "cardbfuel", $("company").value, $("model").value, $("gradeHead").value, $("gradeDetail").value);
				setComboCarDbDsp(strCarCdUrl, "cardbdsp", $("company").value, $("model").value, $("gradeHead").value, $("gradeDetail").value);*/
			}
			else {
				$(comboid).enable();
			}
		} else if(comboid == "formdtlcd" || comboid == "capacd" || comboid == "truck_mnfc" || comboid == "truck_mdl" || comboid == "cpmnfccd" || comboid == "truck_head" || comboid == "capastdcd" || comboid == "formdtl" || comboid == "capacity"){
			if (data.length <= 0) {
				if(comboid == "formdtlcd"){
					
					$("formdtlcd").value = "";
					
					setCapacity(trkCapacityUrl, "capacd", $("formcd").value, $("formdtlcd").value, "적재용량", "");
					
					$("formdtlcd").disable();
					
					if ($("capastdcd") != null) {
						setCapastd(trkCapastdUrl, "capastdcd", $("formcd").value, $("formdtlcd").value, "적재규격", "");
						$("capastdcd").disable();
					}
				
				} else if(comboid == "formdtl"){
					
					$("formdtl").value = "";
					setCapacity(trkCapacityUrl, "capacity", $("form").value, $("formdtl").value, "적재용량", "");
					$("formdtl").disable();
				
				} else if(comboid == "capacd"){
					$("capacd").value = "";
					setTruckMnfc(trkMnfcUrl, "truck_mnfc", $("formcd").value, $("formdtlcd").value, $("capacd").value, "제조사", "");
					$("capacd").disable();
					
					if ($("cpmnfccd") != null) {
						$("cpmnfccd").disable();
					}
					
				} else if(comboid == "capacity"){
					
					$("capacity").value = "";
					setTruckMnfc(trkMnfcUrl, "truck_mnfc", $("form").value, $("formdtl").value, $("capacity").value, "제조사", "");
					$("capacity").disable();
					
				} else if(comboid == "truck_mnfc"){
	
					$("truck_mnfc").value = "";
					setTruckMdl(trkMdlUrl, "truck_mdl", $("formcd").value, $("formdtlcd").value, $("capacd").value, $("truck_mnfc").value, "모델", "");
					$("truck_mnfc").disable();
					
				} else if(comboid == "truck_mdl"){
	
					$("truck_mdl").value = "";
					setTruckHead(trkHeadUrl, "truck_head", $("formcd").value, $("formdtlcd").value, $("capacd").value, $("truck_mnfc").value, $("truck_mdl").value, "등급", "");
					$("truck_mdl").disable();
					
				} else if(comboid == "truck_head"){	
					
					$("truck_head").value = "";
					$("truck_head").disable();
					
				} else if(comboid == "cpmnfccd"){					
					$("cpmnfccd").disable();
					
				} else if(comboid == "capastdcd"){		
					$("capastdcd").disable();
					
				}
				
				
			}
		}
	}


	// 콤보박스 출력
	var colorArray = new Array();	// 색상 콤보 박스는 색상값(expl)을 배열로 갖도록 한다.
	function displayComboSelected_New(responseHttpObj, comboid, initvalue, selectedValue, mnfccd) {	
		var returnData = responseHttpObj.responseText.trim();
		var data = eval("(" + returnData  + ")");
		removeOptions($(comboid));

		addOption($(comboid), "", initvalue);

		for (var i = 0 ; i < data.length ; i++) {
			addOption($(comboid), data[i].abbreviation, data[i].label);

			// 색상 코드인 경우는 아래가 같이 해결 할것.
			if (comboid== "color" && data[i].type == "003") {
				colorArray[data[i].abbreviation] = data[i].expl;
			}
		}

		if (selectedValue != "") {
			$(comboid).value = selectedValue;
		}

		// 세부모델일 경우 1:1 매칭이면 보여주지 않는다.
		if(data.length == 1){
			if($('model') != null) {
				$('model').value = data[0].abbreviation;
			}
			if(comboid == "mdlcd"){
				changeGradeHead(mnfccd, data[0].abbreviation);
			} else if(comboid == "model"){
				emptyCombo("model", "세부모델");
			}
		}

		if (comboid == "mdlcd" || comboid == "modelcd" || comboid == "model" || comboid == "mdl_mdlcd") {
			if (data.length <= 1) {
				if($("mdldisp") != null) {
					$("mdldisp").style.display = "none";
				}
				else {
					$("mdlcd").style.display = "none";
				}
				//changeGradeHead(mnfccd, data[0].abbreviation);
				//changeClsHead(mnfccd, data[0].abbreviation);
			}
			else {
				if($("mdldisp") != null) {
					$("mdldisp").style.display = "block";
				}
				else {
					$("mdlcd").show();
				}
				//emptyCombo(gradeHeadid, "등급");
			}
		}

		if (comboid == "rv_mdlcd" || comboid == "qna_mdlcd") {
			if (data.length <= 1) {
				$(comboid).hide();
			}
			else {
				$(comboid).show();
			}
		}

		if (comboid == "model") {
			if (data.length <= 1) {
				if(mnfccd < 010){
					$(comboid).disable();
				}
				changeGradeHead(mnfccd, data[0].abbreviation);
			}
			else {
				$(comboid).enable();
				emptyCombo(gradeHeadid, "등급");
			}
		}
		
		// 세부등급인 경우는 select 박스의 활성화를 변경한다.
		if (comboid == "gradeDetail" || comboid == "clsdetailcd" || comboid == "mdl_clsdetailcd") {
			if (data.length <= 0) {
				$(comboid).disable();
			}
			else {
				$(comboid).enable();
			}
		}
	}
	
	// 배기량
	function displayComboDspSelected(responseHttpObj, comboid, initvalue, selectedValue) {	
			
		var returnData = responseHttpObj.responseText.trim();
		var data = eval("(" + returnData  + ")");
		removeOptions($(comboid));
		addOption($(comboid), "", initvalue);
		
		for (var i = 0 ; i < data.length ; i++) {
			addOption($(comboid), data[i].vl1+";"+data[i].vl2, data[i].label);
		}
		
		if (selectedValue != "") {
			$(comboid).value = selectedValue;
		}
		
	}
	
	
	function getColorValue(colorValue) {
		return colorArray[colorValue];
	}
	
	/***************************************************************************************/
	/* 연(year)도 콤보박스 생성
	/***************************************************************************************/
	function createYear(id, start_year, end_year, selectedYear, firstOptionText) {
		removeOptions($(id));
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		for(var i = end_year ; i >= start_year ; i--) {
			addOption($(id), i, i + " 년");
		}
		
		if (selectedYear != "") {
			$(id).value = selectedYear;
		}	
	}
	
	/***************************************************************************************/
	/* 연(year)도 콤보박스 생성
	/***************************************************************************************/
	function createYear_chu(yearid, start_year, end_year, selectedYear) {
		removeOptions($(yearid));
		addOption($(yearid), "", "선택");
		
		for(var i = end_year ; i >= start_year ; i--) {
			addOption($(yearid), i, i + "년");
		}
		
		if (selectedYear != "") {
			$(yearid).value = selectedYear;
		}	
	}
	
	function changeYear(yearid, start_year, end_year) {
		createYear(yearid, start_year, end_year);
	}
	
	/***************************************************************************************/
	/* 월(month) 콤보박스 생성
	/***************************************************************************************/
	function createMonth(id, start_month, end_month, selectedMonth, firstOptionText) {
		removeOptions($(id));
		setFirstOption(id, "선택", firstOptionText, "", "");
			
		for(var i = start_month ; i <= end_month ; i++) {
			if(i < 10){
				month = "0"+i;
			}else{
				month = i;
			}
			addOption($(id), month, i + " 월");
		}
		
		if (selectedMonth != "") {
			$(id).value = selectedMonth;
		}
		
	}

	/***************************************************************************************/
	/* 일(day) 콤보박스 생성
	/***************************************************************************************/
	function createDay(dayid, start_day, end_day, selectedDay, unit) {
		addOption($(dayid), "", "선택");
			
		for(var i = start_day ; i <= end_day ; i++) {
			if(i < 10){
				day = "0"+i;
			}else{
				day = i;
			}
			addOption($(dayid), day, i + unit);
		}
				
		if (selectedDay != "") {
			$(dayid).value = selectedDay;
		}
		
	}	

	/***************************************************************************************/
	/* 엔진 콤보박스 생성
	/***************************************************************************************/
	function createEngine(selectid , selectedValue) {
		addOption($(selectid), "", "엔진 선택");
		addOption($(selectid), "1", "DOHC");
		addOption($(selectid), "0", "SOHC");
		
		if (selectedValue != "") {
			$(selectid).value = selectedValue;
		}
	}
	
	// 옵션 추가
	function addOption(comboObj, value, text) {
		var option = new Option();
	
		option.value = value;
        option.text = text;

        comboObj.options.add(option);
	}
	
	// 옵션 삭제
	function removeOptions(comboObj) {
//		var length = comboObj.length;
//		for (var i = 0 ; i < length ; i++) {
//			comboObj.remove(0);
//		}
		comboObj.innerHTML = "";  // 2015.04.10 조광희 - 일부 브라우저 비정상동작 해결
	}
	
	// 데이터를 불러오지 않는 경우 빈 콤보박스 option 추가
	function emptyCombo(idname, emptyvalue) {
		removeOptions($(idname));
		addOption($(idname), "", emptyvalue);
	}
	
	/***************************************************************************************/
	/* 체크박스 컨트롤 함수
	/***************************************************************************************/
	// 체크박스 생성
	function setCheck(strCheckUrl, checkid, mjrcd, checkedValue) {
	    var httpObj = new Ajax.Request(
	        strCheckUrl, {
	        	asynchronous: false, 
	        	parameters: {"mjrcd":mjrcd},  
	            onSuccess: function(responseHttpObj) {
					displayCheck(responseHttpObj, checkid, checkedValue);
				}, 
				onFailure: function() {
	            	displayCheckError(checkid);
	            }
	        }
	    )
	}
	
	// value 타입이 있을 경우 생성
	function setCheckType(strCheckUrl, checkid, mjrcd, valueType, checkedValue) {
	    var httpObj = new Ajax.Request(
	        strCheckUrl, {
	        	asynchronous: false, 
	        	parameters: {"mjrcd":mjrcd, "valueType":valueType},  
	            onSuccess: function(responseHttpObj) {
					displayCheck(responseHttpObj, checkid, checkedValue);
				}, 
				onFailure: function() {
	            	displayCheckError(checkid);
	            }
	        }
	    )
	}
	
	function displayCheck(responseHttpObj, checkid, checkedValue) {
		var returnData = responseHttpObj.responseText.trim();

		var data = eval("(" + returnData  + ")");
		
		var checkedValueArray = checkedValue.split("||");
		
		var tplVal = null;		
		// 템플릿
		var tpl = new Template('<dd><input type="checkbox" name="chk' + checkid + '" id="chk' + checkid + '_#{idx}" value="#{abbreviation}" class="checkbox" #{checked}/><label for="">#{label}</label></dd>');
		
		for (var i = 0 ; i < data.length ; i++) {
			var checked = "";
			
			for (var j = 0 ; j < checkedValueArray.length ; j++) {
				if (checkedValueArray[j] == data[i].abbreviation) {
					checked = "checked";
					break;
				}
			}			
			// 템플릿 매칭
			tplVal = tpl.evaluate({
								idx: i,
								abbreviation: data[i].abbreviation,
								label: data[i].label, 
								checked: checked
						   });

			$(checkid).insert(tplVal);
		}
	}
	
	
	/***************************************************************************************/
	/* 신차정보 연도 생성 함수 : ADD JSI
	/***************************************************************************************/
	// 차량디비 가격정보 화면 데이터 셋팅 
	function setYearData(strCheckUrl, mnfccd, mdlcd, yr){
	    var httpObj = new Ajax.Request(
	        strCheckUrl, {
	        	asynchronous: false, 
	        	//parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd},  
	        	parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "yr":yr},
	            onSuccess: function(responseHttpObj) {
					getYearData(responseHttpObj, mnfccd, mdlcd, yr);
				}, 
				onFailure: function() {
	            	//displayCheckError(checkid);
	            }
	        }
	    )
	}
	
	
	function getYearData(responseHttpObj, mnfccd, mdlcd, yr) {
		var returnData = responseHttpObj.responseText.trim();

		var data = eval("(" + returnData  + ")");
		var lastData = "";
		var yearText = "";
		
		if (data.length != 0)
			yearText = "<p class='year' >";
		
		for (var i = 0 ; i < data.length ; i++) {
			if (i == data.length-1){
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"' class='on'>"+data[i].name+"</a>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"'>"+data[i].name+"</a>";
				}
			}else {
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"' class='on'>"+data[i].name+"</a><span></span>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"'>"+data[i].name+"</a><span></span>";
				}
			}
		}
		
		if (data.length != 0)
			yearText += "</p>";
		
		$("insertYear").innerHTML = yearText;
		
		
		
	}
	
	
	
	
	// 차량디비 제원정보 화면 데이터 셋팅 
	function setDetailYearData(strCheckUrl, mnfccd, mdlcd, yr){
	    var httpObj = new Ajax.Request(
	        strCheckUrl, {
	        	asynchronous: false, 
	        	//parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd},  
	        	parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "yr":yr},
	            onSuccess: function(responseHttpObj) {
					getYearDataDetail(responseHttpObj, mnfccd, mdlcd, yr);
				}, 
				onFailure: function() {
	            	//displayCheckError(checkid);
	            }
	        }
	    )
	}
	
	function getYearDataDetail(responseHttpObj, mnfccd, mdlcd, yr) {
		var returnData = responseHttpObj.responseText.trim();
		

		var data = eval("(" + returnData  + ")");
		var lastData = "";
		var yearText = "";
		 
		if (data.length != 0)
			yearText = "<p class='year' >";
		
		for (var i = 0 ; i < data.length ; i++) {
			if (i == data.length-1){
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?method=detail&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' class='on'>"+data[i].name+"</a>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?method=detail&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"'>"+data[i].name+"</a>";
				}
			}
			else{
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?method=detail&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"' class='on'>"+data[i].name+"</a><span></span>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?method=detail&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"'>"+data[i].name+"</a><span></span>";
				}
			}
		}
		
		if (data.length != 0)
			yearText += "</p>";
		
		//alert(yearText);
		
		$("insertYear").innerHTML = yearText;
	}
	
	// 차량디비 사진  화면 데이터 셋팅 
	function setYearDataCatalog(strCheckUrl, mnfccd, mdlcd, yr){
	    var httpObj = new Ajax.Request(
	        strCheckUrl, {
	        	asynchronous: false, 
	        	//parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd},  
	        	parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "yr":yr},
	            onSuccess: function(responseHttpObj) {
					getYearDataCatalog(responseHttpObj, mnfccd, mdlcd, yr);
				}, 
				onFailure: function() {
	            	//displayCheckError(checkid);
	            }
	        }
	    )
	}
	
	
	function getYearDataCatalog(responseHttpObj, mnfccd, mdlcd, yr) {
		var returnData = responseHttpObj.responseText.trim();

		var data = eval("(" + returnData  + ")");
		var lastData = "";
		var yearText = "";
		
		if (data.length != 0)
			yearText = "<p class='year' >";
		
		for (var i = 0 ; i < data.length ; i++) {
			if (i == data.length-1){
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?method=catalog&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"' class='on'>"+data[i].name+"</a>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?method=catalog&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"'>"+data[i].name+"</a>";
				}
			}else{ 
				if (yr == data[i].name){
					yearText += "<a href='/dc/dc_catalog.do?method=catalog&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"' class='on'>"+data[i].name+"</a><span></span>";
				}else{
					yearText += "<a href='/dc/dc_catalog.do?method=catalog&company="+mnfccd+"&model="+mdlcd+"&yr="+data[i].name+"' id='"+data[i].name+"'>"+data[i].name+"</a><span></span>";
				}
			}
		}
		
		if (data.length != 0)
			yearText += "</p>";
		
		//alert(yearText);
		
		$("insertYear").innerHTML = yearText;
	}
			
	/***************************************************************************************/
	/* 주행거리 콤보박스 생성
	/***************************************************************************************/
	function createCarleng(id, start, end, selected, firstOptionText) {
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		for(var i = start ; i <= end ; i=i+10000) {
			addOption($(id), i, commify(i) + " Km");
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}	
	
	/***************************************************************************************/
	/* 트럭용 주행거리 콤보박스 생성
	/***************************************************************************************/
	var ArrTruckLeng = new Array();
	ArrTruckLeng = ['50000','100000','150000','200000','250000','300000','400000','500000','600000','700000','800000','900000','1000000'];
	
	function createTruckleng(id, start, end, selected, firstOptionText) {
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		var chk = 0;
		
		//alert(start + "," + end);
		for(var i = start ; i < 13 ; i++) {
			addOption($(id), ArrTruckLeng[i], commify(ArrTruckLeng[i]) + " Km");

			if (selected != "" &&  ArrTruckLeng[i] ==selected ) {
				chk++;
			}
		}
		
		if (selected != ""&& chk > 0) {
			$(id).value = selected;
		}	
	}	
	
	function changTruckleng(id, start, end, selected, firstOptionText) {
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		var chk = 0;
		
		//alert(start + "," + end);
		for(var i = start ; i < 13 ; i++) {
			addOption($(id), ArrTruckLeng[i], commify(ArrTruckLeng[i]) + " Km");
			if (selected != "" &&  ArrTruckLeng[i] ==selected ) {
				chk++;
			}
		}
		
		if (selected != "" && chk > 0) {
			$(id).value = selected;
		}	
	}
	
	var ArrCarLeng = new Array();
	ArrCarLeng = ['0','10000','20000','30000','40000','50000','60000','70000','80000','90000','100000','110000','120000','130000','140000','150000','160000','170000','180000','190000','200000'];
	function changCarleng(id, start, end, selected, firstOptionText) {
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		
		//alert(start + "," + end);
		for(var i = start ; i < 21 ; i++) {
			if (start != 21) {
				addOption($(id), ArrCarLeng[i], commify(ArrCarLeng[i]) + " Km");
			}
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}	
	//중고차시세용
	function changCarlengPrPrice(id, start, end, selected) {
		addOption($(id), "", "선택");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		
		//alert(start + "," + end);
		for(var i = start ; i < end ; i++) {
			if (start != 21) {
				addOption($(id), ArrCarLeng[i], commify(ArrCarLeng[i]) + " Km");
			}
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}
	/***************************************************************************************/
	/* 가격 콤보박스 생성
	/***************************************************************************************/
	function createDmndprc(id, start, end, selected, firstOptionText) {
		removeOptions($(id));
		setFirstOption(id, "선택", firstOptionText, "", "");
		
		//alert(start + "," + end);
		var sumprc = 100;
		for(var i = start ; i <= end ; i=i+sumprc) {
			addOption($(id), i, commify(i) + " 만원"); 
			if (i >= 2000) {
				sumprc = 1000;
			}
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}
	
	var ArrCarDmndprc = new Array();
	ArrCarDmndprc = ['100','200','300','400','500','600','700','800','900','1000','1100','1200','1300','1400','1500','1600','1700','1800','1900','2000','3000','4000','5000','6000','7000'];	
	function changDmndprc(id, start, end, selected) {
		addOption($(id), "", "선택");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		
		//alert(start + "," + end);
		for(var i = start ; i < 25 ; i++) {
			if (start != 25) {
				addOption($(id), ArrCarDmndprc[i], commify(ArrCarDmndprc[i]) + " 만원");
			}
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}
	
	/**
	 * start부터 end까지 selectbox에 값을 넣는다.
	 * @param id	selectboxID
	 * @param start	시작값
	 * @param end	종료값
	 * @param increaseVal	증가값
	 * @param selected	선택되어질값
	 * @param unit	option값에 붙어질 값
	 */
	function orderSelectBoxSet(id, start, end, increaseVal, selected, unit) {
		addOption($(id), "-1", "선택");
		
		if (start == '') {
			start = 0;
		} else {
			start = start;
		}
		
		if(!increaseVal || increaseVal == '' || increaseVal < 0) increaseVal = 1;
		
		for(var i = start ; i <= end ; i = i + increaseVal) {
			addOption($(id), i, i + unit);
		}
		
		if (selected != "") {
			$(id).value = selected;
		}	
	}

	/**
	 * select box 의 첫번째 option을 설정한다.
	 * 
	 * @param id	selectbox객체 ID
	 * @param defaultText	기본 option text 값
	 * @param text	    	option text 값
	 * @param defaultValue	기본 option value 값
	 * @param value			option value 값
	 */
	function setFirstOption(id, defaultText, text, defaultValue, value) {
		if(text == null) {
			text = defaultText;
		}
		if(value == null) {
			value = defaultValue;
		}
		addOption($(id), value, text);
	}