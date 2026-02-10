from fastapi import APIRouter, HTTPException

from config.products import get_product_by_name, get_product_names
from utils.logger import log_feature_end, log_feature_fail, log_feature_start

router = APIRouter()


@router.get("/")
async def list_products():
    log_feature_start("products_list")
    names = get_product_names()
    log_feature_end("products_list")
    return {"products": names}


@router.get("/{product_name}")
async def get_product_detail(product_name: str):
    log_feature_start("products_detail", product_name)
    product = get_product_by_name(product_name)
    if not product:
        log_feature_fail("products_detail", f"Product '{product_name}' not found")
        raise HTTPException(
            status_code=404, detail=f"Product '{product_name}' not found"
        )
    res = product.model_dump() if hasattr(product, "model_dump") else product.__dict__
    log_feature_end("products_detail")
    return res
