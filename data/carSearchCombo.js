	var setForm = function(strComboUrl, comboid, initvalue, selectedValue) { 
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}

	var setFormDtl = function(strComboUrl, comboid, formcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	var setCapacity = function(strComboUrl, comboid, formcd, formdtlcd, initvalue, selectedValue) { 
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}	
	
	var setCapaMnfc = function(strComboUrl, comboid, formcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	var setCapastd = function(strComboUrl, comboid, formcd, formdtlcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	var setTruckMnfc = function(strComboUrl, comboid, formcd, formdtlcd, capacd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd, "capacd":capacd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}		
	
	var setTruckMdl = function(strComboUrl, comboid, formcd, formdtlcd, capacd, truck_mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd, "capacd":capacd, "truck_mnfccd":truck_mnfccd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}		
	
	var setTruckMdl_Mdlnm = function(strComboUrl, comboid, formcd, formdtlcd, capacd, truck_mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd, "capacd":capacd, "truck_mnfccd":truck_mnfccd, "orderType":"mdlnm"},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	var setTruckHead = function(strComboUrl, comboid, formcd, formdtlcd, capacd, truck_mnfccd, truck_mdlcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"formcd":formcd, "formdtlcd":formdtlcd, "capacd":capacd, "truck_mnfccd":truck_mnfccd , "truck_mdlcd":truck_mdlcd},
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	//전문업체 목록 출력
	function setTruckConpanylist(strComboUrl, comboid, formcd, initvalue, selectedValue) { 
		var httpObj = new Ajax.Request (
				strComboUrl, {
					asynchronous: false,
					parameters: {"formcd":formcd},   
					onSuccess: function(responseHttpObj) {
						displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
					}, 
					onFailure: function() {
		            	displayError(comboid, initvalue);
		            }
				}
			)
	}
	// 제조사 출력 
	// param : carType 추가 JSI 20120522 국산차 수입차 구분 
	function setCompany(strComboUrl, comboid, initvalue, selectedValue, carType) { 
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"carType":carType},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue, carType);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}

	// 모델 그룹 출력
	function setModelGroup(strComboUrl, comboid, mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}

	// 모델 출력
	function setModel(strComboUrl, comboid, mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "orderType":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	function setModel_Mdlnm(strComboUrl, comboid, mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "orderType":"mdlnm"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 모델 출력
	function setModel_New(strComboUrl, comboid, mnfccd, mdlgroupcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlgroupcd":mdlgroupcd},   
				onSuccess: function(responseHttpObj) {
					if(mdlgroupcd != ""){
						displayComboSelected_New(responseHttpObj, comboid, initvalue, selectedValue, mnfccd);
					} else {
						displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
					}
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 등급 출력
	function setGradeHead(strComboUrl, comboid, mnfccd, mdlcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 등급 출력 (모델비교용)
	function setGradeHead2(strComboUrl, comboid, mnfccd, mdlcd, caryear, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "caryear":caryear, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 세부등급 출력
	// combotype 추가 by iheart79
	function setGradeDetail(strComboUrl, comboid, mnfccd, mdlcd, clsheadcd, initvalue, selectedValue, comboType) {
		
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "valueType:":"name", "comboType":comboType},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue, comboType);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 세부등급 출력 (모델비교용)
	function setGradeDetail2(strComboUrl, comboid, mnfccd, mdlcd, caryear, clsheadcd, initvalue, selectedValue, comboType) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "caryear":caryear, "clsheadcd":clsheadcd, "valueType:":"name", "comboType":comboType},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue, comboType);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 구.군 출력
	function setGugun(strComboUrl, comboid, sido, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"sido":sido},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	
	// 차종별 모델 검색
	function setTypeModel(strComboUrl, comboid, ctgr, initValue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"ctgr":ctgr},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initValue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 수입 브랜드 인증차량 판매지역 검색
	function setRegion(strComboUrl, comboid, mnfccd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 연식출력
	function setCarYear(strComboUrl, comboid, mnfccd, mdlcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 기관 출력
	function setCarCrash(strComboUrl, comboid, mnfccd, mdlcd, year, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "caryear":year, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
		
	// 배기량
	function setComboDsp(strComboUrl, comboid, mjrcd, valueType, initvalue, selectedValue) { 
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mjrcd":mjrcd, "valueType":valueType},
				onSuccess: function(responseHttpObj) {
					displayComboDspSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError( comboid, initvalue);
	            }
			}
		)
	}	
	
	
	/************************************************************************************/
	/* 색상선택시 컬러변경하기 */
	/************************************************************************************/	
	function changeColorVal(colorcode) {
		var colorValue = getColorValue(colorcode);
		if( colorcode != ""){

			var leftClr = colorValue.substring(0,7);
			var rightClr = colorValue.substring(8,17);
	
			$("leftClr").style.backgroundColor = leftClr;
			$("rightClr").style.backgroundColor = rightClr;
		}
		//웹칼라코드가 없을때
		else {
		
			$("leftClr").style.backgroundColor = "#FFFFFF";
			$("rightClr").style.backgroundColor = "#FFFFFF";
		}
		
	}
	function changeMnfc(carType) {
		var strCompanyUrlType = strCompanyUrl + "&carType=" + carType;
		
		// 제조사
		setCompany(strCompanyUrlType, companyid, "제조사", "");
		
		setModel(strModelUrl, modelid, "", "모델", "");
	}
	function changeModel(mnfccd) {
		setModel(strModelUrl, modelid, mnfccd, "모델", "");
	}	

	
	function setCarYrMksdt(strComboUrl, comboid, mnfccd, mdlcd, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}

	// 등급 출력-jato
	function setDBGradeHead(strComboUrl, comboid, mnfccd, mdlcd, year, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "year":year, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}
	
	// 세부등급 출력-jato
	function setDBGradeDetail(strComboUrl, comboid, mnfccd, mdlcd, clsheadcd, year, initvalue, selectedValue) {
		var httpObj = new Ajax.Request (
			strComboUrl, {
				asynchronous: false,
				parameters: {"mnfccd":mnfccd, "mdlcd":mdlcd, "clsheadcd":clsheadcd, "year":year, "valueType:":"name"},   
				onSuccess: function(responseHttpObj) {
					displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
				}, 
				onFailure: function() {
	            	displayError(comboid, initvalue);
	            }
			}
		)
	}	
	
	// 웹예약 가능 차량 조회
    function setWebresCompany(strComboUrl, comboid, initvalue, selectedValue, carType, centercd, grade) { 
        var httpObj = new Ajax.Request (
            strComboUrl, {
                asynchronous: false,
                parameters: {"carType":carType, "centercd":centercd,"grade":grade},   
                onSuccess: function(responseHttpObj) {
                    displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue, carType);
                }, 
                onFailure: function() {
                    displayError(comboid, initvalue);
                }
            }
        )
    }	

    // 웹예약 가능 모델 조회
    function setWebresModel(strComboUrl, comboid, mnfccd, initvalue, selectedValue, centercd, grade) { 
        var httpObj = new Ajax.Request (
            strComboUrl, {
                asynchronous: false,
                parameters: {"mnfccd":mnfccd, "centercd":centercd,"grade":grade},   
                onSuccess: function(responseHttpObj) {
                    displayComboSelected(responseHttpObj, comboid, initvalue, selectedValue);
                }, 
                onFailure: function() {
                    displayError(comboid, initvalue);
                }
            }
        )
    }
    
	