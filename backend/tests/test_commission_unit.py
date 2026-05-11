from app.core.commission.schemas import CommissionConfig
from app.core.commission.service import calculate_breakdown


def test_calculate_breakdown_percentage_only():
    config = CommissionConfig(
        owner_percent=5.0,
        owner_fixed=0.0,
        customer_percent=3.0,
        customer_fixed=0.0,
    )
    result = calculate_breakdown(1000.0, "INR", config)
    assert result["platform_commission"] == 50.0
    assert result["service_fee"] == 30.0
    assert result["owner_payout"] == 950.0
    assert result["customer_total"] == 1030.0


def test_calculate_breakdown_with_fixed_fees():
    config = CommissionConfig(
        owner_percent=5.0,
        owner_fixed=25.0,
        customer_percent=3.0,
        customer_fixed=50.0,
    )
    result = calculate_breakdown(1000.0, "INR", config)
    assert result["platform_commission"] == 75.0
    assert result["service_fee"] == 80.0
    assert result["owner_payout"] == 925.0
    assert result["customer_total"] == 1080.0


def test_calculate_breakdown_zero_config():
    config = CommissionConfig()
    result = calculate_breakdown(500.0, "USD", config)
    assert result["platform_commission"] == 0.0
    assert result["service_fee"] == 0.0
    assert result["owner_payout"] == 500.0
    assert result["customer_total"] == 500.0


def test_calculate_breakdown_none_config():
    result = calculate_breakdown(500.0, "USD", None)
    assert result["platform_commission"] == 0.0
    assert result["service_fee"] == 0.0
    assert result["owner_payout"] == 500.0
    assert result["customer_total"] == 500.0


def test_commission_config_defaults():
    config = CommissionConfig()
    assert config.owner_percent == 0.0
    assert config.owner_fixed == 0.0
    assert config.customer_percent == 0.0
    assert config.customer_fixed == 0.0
    assert config.currency == "USD"


def test_commission_config_from_dict():
    data = {
        "owner_percent": 10.0,
        "customer_percent": 5.0,
        "customer_fixed": 100.0,
        "currency": "INR",
    }
    config = CommissionConfig(**data)
    assert config.owner_percent == 10.0
    assert config.owner_fixed == 0.0
    assert config.customer_fixed == 100.0
