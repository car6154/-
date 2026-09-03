import pandas as pd

def test_logic():
    # target options
    target_options = ["스마트 크루즈 컨트롤(SCC)", "서라운드 뷰 모니터(SVM)"]
    
    # market data mockup
    df = pd.DataFrame({
        '판매가_num': [2000, 2200, 2500, 2600],
        '옵션리스트': [
            [],
            ["내비게이션"],
            ["스마트 크루즈 컨트롤(SCC)", "내비게이션"],
            ["서라운드 뷰 모니터(SVM)", "스마트 크루즈 컨트롤(SCC)"]
        ]
    })
    
    if target_options:
        # Check if market car has ANY of the target options
        has_target_opt = df['옵션리스트'].apply(lambda opts: any(opt in target_options for opt in opts))
        target_opt_avg = int(df[has_target_opt]['판매가_num'].mean()) if has_target_opt.any() else 0
        no_target_opt_avg = int(df[~has_target_opt]['판매가_num'].mean()) if (~has_target_opt).any() else 0
        print(f"타겟 차량 옵션 포함 매물 평균: {target_opt_avg}")
        print(f"타겟 차량 옵션 미포함 매물 평균: {no_target_opt_avg}")

test_logic()
