const { customAlphabet } = require("nanoid")
const { VALID_CHARACTER_TO_GENERATE_INVITE_CODE } = require("../constants")

const generateInviteCode = () => {
    const inviteCodeGenerator = customAlphabet(VALID_CHARACTER_TO_GENERATE_INVITE_CODE, 8)
    const inviteCode = inviteCodeGenerator()
    return inviteCode
}

module.exports = {
    generateInviteCode
}