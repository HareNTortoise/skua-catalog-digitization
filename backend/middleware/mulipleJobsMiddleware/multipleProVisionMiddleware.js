require("dotenv").config();
const { GoogleGenerativeAI } = require("@google/generative-ai");
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

const get_multiple_image = async (image) => {
  const image_prompt = `I am providing list of JSON attributes
    product_name [String]
    description [Text]
    price [Float]
    quantity [Float]
    categories [list of String]
    net_weight [Float]
    barcode [String]
    manufacturer_brand [String]
    manufacturing_date [String] [DD-MM-YYYY]
    expiration_date [String]  [DD-MM-YYYY]
  
    Find the attributes using the image given below, the attributes not found in the image should be filled with null value.
    Do not fill quantity of stock as it will not be mentioned in the image.
    Generate the categories and description based on product image
    The dates should be in the format [DD-MM-YYYY] id found in the image
    THE OUTPUT IS TO BE GIVEN IN JSON FORMAT
    The user entered image is below :`;
  const model = genAI.getGenerativeModel({ model: "gemini-pro-vision" });

  const imageParts = [
    {
      inlineData: {
        data: image,
        mimeType: "image/jpeg",
      },
    },
  ];

  const result = await model.generateContent([image_prompt, ...imageParts]);
  const response = result.response;
  const text = response.text();

  const cleanTextOutput = text
    .trim()
    .replace(/^```/, "")
    .replace(/```$/, "")
    .replace(/json/gi, "");
  const responseJson = JSON.parse(cleanTextOutput);
  return responseJson;
};

module.exports = get_multiple_image;
