from pydantic import BaseModel, Field
from typing import List, Optional

# --- API Schemas ---


class PresignedUrlRequest(BaseModel):
    store_id: Optional[str] = None
    filename: str
    notify_email: Optional[str] = None


class PresignedUrlResponse(BaseModel):
    job_id: str
    upload_url: str


class UploadAndQueueResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    items_processed: Optional[int] = 0


class SKUItemResponse(BaseModel):
    id: str
    store_id: str
    job_id: Optional[str] = None

    product_name: str
    description: Optional[str] = None
    mrp: Optional[float] = None
    selling_price: Optional[float] = None
    quantity: Optional[float] = None
    categories: Optional[str] = None
    net_weight: Optional[float] = None
    unit_of_measurement: Optional[str] = None
    colour: Optional[str] = None
    size: Optional[str] = None
    packaging_type: Optional[str] = None
    barcode: Optional[str] = None
    sku_id: Optional[str] = None
    manufacturer_brand: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiration_date: Optional[str] = None
    image_url: Optional[str] = None
    requires_review: bool = False


class CatalogResponse(BaseModel):
    items: List[SKUItemResponse]

# --- LLM Extraction Schema ---


class LLMExtractedSKU(BaseModel):
    product_name: str = Field(description="The recognizable name of the product")
    barcode: Optional[str] = Field(description="The numeric barcode, if visually readable or provided in the answer key")
    manufacturer_brand: Optional[str] = Field(description="The brand or company name")
    selling_price: Optional[float] = Field(description="The selling price spoken by the user")
    quantity: Optional[float] = Field(description="The inventory stock count spoken by the user")
    packaging_type: str = Field(description="Categorize as 'SINGLE_UNIT', 'MULTIPACK', or 'CARTON'")
    net_weight: Optional[float] = Field(description="The numeric weight or volume")
    unit_of_measurement: Optional[str] = Field(description="The unit for the weight (e.g., 'g', 'kg', 'ml', 'L')")
    colour: Optional[str] = Field(description="Dominant colour of the product")
    size: Optional[str] = Field(description="Size category (e.g., 'Small', 'Large')")
    categories: List[str] = Field(description="1-3 relevant e-commerce categories")
    description: Optional[str] = Field(description="A short, 1-sentence generated description")
    manufacturing_date: Optional[str] = Field(description="Mfd date printed on packaging")
    expiration_date: Optional[str] = Field(description="Exp date or Best Before printed on packaging")
    requires_review: bool = Field(description="Set to true if audio/visuals are unclear")
    timestamp_mentioned: str = Field(description="The MM:SS timestamp where this product was focused")


class VideoExtractionResult(BaseModel):
    items: List[LLMExtractedSKU]
