"""test_marketplace.py - E005."""
def test_list_skill():
    from aios_kernel.product.marketplace import MarketplaceService
    m = MarketplaceService()
    l = m.list_skill("skill_1", "seller_a", price_usd=9.99)
    assert l.price_usd == 9.99


def test_purchase():
    from aios_kernel.product.marketplace import MarketplaceService
    m = MarketplaceService()
    l = m.list_skill("skill_1", "seller_a")
    receipt = m.purchase_skill("buyer_b", str(l.id))
    assert receipt["seller_share"] == 9.99 * 0.7
    assert receipt["platform_share"] == 9.99 * 0.3


def test_rating_initial_zero():
    from aios_kernel.product.marketplace import MarketplaceService
    m = MarketplaceService()
    l = m.list_skill("skill_2", "seller_b")
    assert l.rating == 0.0


def test_revenue_split():
    from aios_kernel.product.marketplace import MarketplaceService
    m = MarketplaceService()
    l = m.list_skill("skill_3", "seller_c", 100.0)
    r = m.purchase_skill("buyer_d", str(l.id))
    assert abs(r["seller_share"] - 70.0) < 0.01
    assert abs(r["platform_share"] - 30.0) < 0.01


def test_sales_count_increments():
    from aios_kernel.product.marketplace import MarketplaceService
    m = MarketplaceService()
    l = m.list_skill("skill_4", "seller_e")
    m.purchase_skill("buyer1", str(l.id))
    m.purchase_skill("buyer2", str(l.id))
    assert l.sales_count == 2
