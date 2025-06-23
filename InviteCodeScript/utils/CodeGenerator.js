const { VALID_CHARACTER_TO_GENERATE_INVITE_CODE } = require("../constants")
const crypto = require("crypto")

const generateCode = () => {
    const length = 8;
    let code = "";
    for (let i = 0; i < length; i++) {
        const randomIndex = crypto.randomInt(0,  VALID_CHARACTER_TO_GENERATE_INVITE_CODE.length);
        code += VALID_CHARACTER_TO_GENERATE_INVITE_CODE[randomIndex];
    }
    return code
}

module.exports = {
    generateCode
}