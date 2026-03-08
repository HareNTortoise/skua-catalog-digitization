# (SKUA)Shelfie - Multi-Modal Product Catalog Digitization Platform

Shelfie helps sellers digitize large product catalogs seamlessly using text, voice, and image inputs, supporting 10+ Indic languages through India's Bhashini model and Data Vatika integration.

## Overview

Shelfie is designed for sellers managing catalogs with 1000+ SKUs, enabling efficient product data capture through multiple input methods:

- **Text Input**: Direct entry in 10+ Indic languages
- **Voice Input**: Speech-to-text conversion with Bhashini integration
- **Image Input**: Intelligent product recognition and auto-fill from repository

## Key Features

- **Multi-Modal Input**: Seamlessly combine text, voice, and image inputs for single product entries
- **Indic Language Support**: Full support for 10+ Indian languages via Bhashini
- **Intelligent Pre-filling**: Scan product images to automatically populate product names
- **Large-Scale Processing**: Handle catalogs with 1000+ SKUs efficiently
- **Data Enhancement**: Leverage Data Vatika for improved data quality and insights
- **Bulk Operations**: Import/export catalogs in multiple formats (CSV, JSON, Excel)

## Product Attributes

Capture comprehensive product information:
- SKU ID
- Product Name
- Description
- Price
- Images
- Inventory Count
- Colour
- Size
- Brand
- Custom Attributes

## Architecture

Shelfie follows a microservices architecture with:

- **Multi-Modal Processor**: Orchestrates text, voice, and image input handling
- **Catalog Manager**: Manages product catalogs and bulk operations
- **Voice Processor**: Converts speech to text using Bhashini
- **Image Recognition Engine**: Matches products and pre-fills data
- **External Integrations**: Bhashini API and Data Vatika services

## Getting Started

### Prerequisites

- Node.js 18+ or compatible runtime
- Access to Bhashini API credentials
- Access to Data Vatika API credentials
- Redis for caching (optional but recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd shelfie

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with your API credentials

# Run tests
npm test

# Start development server
npm run dev
```

### Configuration

Create a `.env` file with the following:

```env
BHASHINI_API_KEY=your_bhashini_api_key
BHASHINI_API_URL=https://api.bhashini.gov.in
DATA_VATIKA_API_KEY=your_data_vatika_key
DATA_VATIKA_API_URL=https://api.datavatika.gov.in
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://localhost:5432/shelfie
```

## Usage

### Creating a Catalog

```typescript
const catalog = await catalogManager.createCatalog(sellerId, {
  name: "My Product Catalog",
  description: "Electronics and accessories"
});
```

### Adding Products with Multi-Modal Input

```typescript
// Scan product image
const imageResult = await imageRecognition.extractProductInfo(imageData);

// Pre-fill product name from image match
const productData = {
  skuId: "SKU-001",
  productName: imageResult.matchedProduct.name,
  // ... other attributes
};

// Add voice input for description
const voiceResult = await voiceProcessor.convertSpeechToText(audioData, "hi");
productData.description = voiceResult.text;

// Save product
await catalogManager.addProduct(catalog.catalogId, productData);
```

## Supported Languages

- Hindi (hi)
- Bengali (bn)
- Tamil (ta)
- Telugu (te)
- Marathi (mr)
- Gujarati (gu)
- Kannada (kn)
- Malayalam (ml)
- Punjabi (pa)
- Odia (or)
- And more...

## Development

### Project Structure

```
shelfie/
├── src/
│   ├── core/              # Core data models and interfaces
│   ├── catalog/           # Catalog management
│   ├── multimodal/        # Multi-modal input processing
│   ├── voice/             # Voice processing
│   ├── image/             # Image recognition
│   ├── integrations/      # External service integrations
│   └── api/               # REST API endpoints
├── tests/                 # Test suites
├── docs/                  # Additional documentation
└── .kiro/specs/shelfie/   # Feature specifications
```

### Running Tests

```bash
# Run all tests
npm test

# Run property-based tests
npm run test:property

# Run integration tests
npm run test:integration

# Run with coverage
npm run test:coverage
```

## Performance

- Individual SKU processing: < 3 seconds
- Concurrent catalog uploads: 10+ simultaneous operations
- Voice recognition accuracy: 95%+
- Image matching accuracy: 80%+ for common products
- Catalog size support: 1000+ SKUs with consistent performance

## API Documentation

API documentation is available at `/api/docs` when running the development server.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [docs-url]
- Email: support@shelfie.example

## Acknowledgments

- **Bhashini**: India's language technology platform
- **Data Vatika**: Enhanced data processing capabilities
- Built with support from India's digital infrastructure initiatives
