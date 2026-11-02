"""'2종 자판기' — brand-product sourcing automation.

Machine 1 (Kick Monitor): watches sourcing sites (무신사/29cm/오케이몰 ...) per
brand, detects new products and price drops, and pushes alerts.

Machine 2 (품번 소싱표): matches sourcing-site items to the same 품번(style
code) sold by Naver 직구 stores, applies stacked coupons to our cost, and
writes every row with enough margin into an Excel sourcing sheet — no detail
page needed, because the listing is a verified brand product.
"""
