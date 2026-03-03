require("dotenv").config();
const { GoogleGenerativeAI } = require("@google/generative-ai");
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

const get_text = async (query, bool = true) => {
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
  const text_prompt = `I am providing list of JSON attributes
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
  
                    Find the attributes in user entered prompt below, the attributes not found in the user entered prompt should be filled with null value.
                    The dates should be in the format [DD-MM-YYYY] id found in the user entered prompt
                    THE OUTPUT IS TO BE GIVEN IN JSON FORMAT
                    The user entered prompt is below :`;

  let prompt = text_prompt + query;
  const result = await model.generateContent(prompt);
  const response = result.response;
  const text = response.text();
  const cleanTextOutput = text
    .trim()
    .replace(/^```/, "")
    .replace(/```$/, "")
    .replace(/json/gi, ""); // Modified this line to use the text variable
  const responseJson = JSON.parse(cleanTextOutput);
  return responseJson;
};

module.exports = get_text;
