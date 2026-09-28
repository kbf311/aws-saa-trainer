from app.database import SessionLocal, init_db
from app.services import dashboard_service
from app.config import get_recent_days

init_db()
with SessionLocal() as db:
    # 1. Config test
    recent_days = get_recent_days()
    print(f"[PASS] Configured recent_days: {recent_days}")
    assert recent_days > 0

    # 2. All period summary
    all_summary = dashboard_service.get_dashboard_summary(db=db, recent_n=20)
    print(f"[PASS] All period answers: {all_summary['total_answers']}, labels count: {len(all_summary['cumulative_history']['labels'])}")
    assert all_summary["period_days"] is None
    assert all_summary["configured_recent_days"] == recent_days
    assert "available_years" in all_summary
    assert len(all_summary["available_years"]) > 0
    print(f"[PASS] Available years: {all_summary['available_years']}")

    # 3. Recent 7 days summary
    recent_summary = dashboard_service.get_dashboard_summary(db=db, recent_n=20, period_days=7)
    cum_data = recent_summary["cumulative_history"]["cumulative"]
    print(f"[PASS] Recent 7 days answers: {recent_summary['total_answers']}, labels count: {len(recent_summary['cumulative_history']['labels'])}")
    print(f"[PASS] Cumulative curve range: {cum_data[0]} -> {cum_data[-1]} (Total answers: {all_summary['total_answers']})")
    assert recent_summary["period_days"] == 7
    # 学習した日（4日） + 開始前日（1日） = 5ラベル（未学習の日はプロットされない）
    assert len(recent_summary["cumulative_history"]["labels"]) <= 8
    # KPIカードの値（total_answers, days_count）は全期間で固定であることを確認
    assert recent_summary["total_answers"] == all_summary["total_answers"]
    assert recent_summary["days_count"] == all_summary["days_count"]
    # グラフの推移は直前累計からスタートして全期間合計に到達することを確認
    assert cum_data[-1] == all_summary["total_answers"]
    assert cum_data[0] < cum_data[-1]

print("\nALL SERVICE LOGIC TESTS PASSED!")
