var express = require('express');
const fs = require('fs');
require('dotenv').config();

const { GoogleGenerativeAI } = require("@google/generative-ai");
var router = express.Router();
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

const get_audio = async (audio, lang_code = "en") => {
    var modelId = null; // Fill in the modelId
    const source = lang_code;
    const bhashaniData = fs.readFileSync('constants/bhashini.json', 'utf8');
    const bhashaniJson = JSON.parse(bhashaniData);
    for (const item of bhashaniJson) {
        if (item.lang_code === lang_code) {
            modelId = item.model_id;
            break;
        }
    }
    
    const bhashini_input = {
        modelId,
        task: "asr",
        audioContent: audio,
        source,
        userId: null
    };

    const bhashini_api = "https://meity-auth.ulcacontrib.org/ulca/apis/asr/v1/model/compute";

    var input = {
        modelId: modelId,
        task: "asr",
        audioContent: audio,
        source: source,
        userId: null
    };

    const response = await fetch(bhashini_api, {
        method: 'POST',
        body: JSON.stringify(input),
        headers: {
            'Content-Type': 'application/json' // Specify the content type as JSON
        }
    });

    if (response.status === 200) {
        const data = await response.json();
        await get_text(data.data.source, false);
    } else {
        return "Error in fetching audio data";
    }
};


module.exports = router;