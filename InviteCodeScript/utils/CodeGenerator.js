const { customAlphabet } = require("nanoid")
const { VALID_CHARACTER_TO_GENERATE_INVITE_CODE } = require("../constants")

const generateCode = () => {
    const CodeGenerator = customAlphabet(VALID_CHARACTER_TO_GENERATE_INVITE_CODE, 8)
    const code = CodeGenerator()
    return code
}

module.exports = {
    generateCode
}