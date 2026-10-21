from app.data.stats import stats_from_closes
from app.scoring import SectorMember, TickerInput, score_ticker, sector_call


def test_no_data_gives_no_signal():
    r = score_ticker(TickerInput(price=None))
    assert r.score is None and r.signal is None


def test_big_upside_cheap_stock_is_buy():
    r = score_ticker(TickerInput(price=100, target=125, pe=12, sector_pe=24, ch1m=2, ch3m=4))
    assert r.signal == "buy"
    assert r.horizon == "long"
    assert "upside to target" in r.reasons


def test_price_above_target_and_expensive_is_sell():
    r = score_ticker(TickerInput(price=100, target=85, pe=60, sector_pe=25, ch1m=-6, ch3m=-10))
    assert r.signal == "sell"


def test_stop_loss_breach_always_sells():
    r = score_ticker(TickerInput(price=90, target=150, stop_loss=92, ch1m=8))
    assert r.signal == "sell"
    assert r.reasons == ["at or below stop-loss"]


def test_strong_trend_on_rich_valuation_suggests_short_horizon():
    r = score_ticker(
        TickerInput(price=120, ch1m=9, ch3m=18, dma50=110, dma200=100, pe=50, sector_pe=30)
    )
    assert r.horizon_suggested == "short"


def test_horizon_override_wins():
    r = score_ticker(
        TickerInput(price=120, ch1m=9, ch3m=18, dma50=110, dma200=100, pe=50, sector_pe=30, horizon_override="long")
    )
    assert r.horizon_suggested == "short" and r.horizon == "long"


def test_sector_weighted_by_invested_money():
    avg, call = sector_call([SectorMember(80, 900_000), SectorMember(20, 100_000)])
    assert avg == 74.0 and call == "overweight"


def test_sector_equal_weight_when_amounts_missing():
    avg, call = sector_call([SectorMember(80, 900_000), SectorMember(20, None)])
    assert avg == 50.0 and call == "neutral"


def test_stats_from_closes():
    closes = [100.0] * 230 + [110.0] * 20 + [121.0]
    s = stats_from_closes(closes)
    assert s.ch1m == 21.0  # 121 vs 100, 22 sessions back
    assert s.high52 == 121.0 and s.low52 == 100.0
    assert s.dma50 is not None and s.dma200 is not None
