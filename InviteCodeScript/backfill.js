const dotenv = require("dotenv")
const User = require("./UserModel")
const { connect, disconnect } = require("./utils/database")
const { generateInviteCode } = require("./utils/InviteCodeGenerator")
const { activityLogger, errorLogger } = require("./utils/logger")

dotenv.config({ path: "./config.env" });

const backFillInviteCode = async() => {
    try {
        activityLogger.info(`Connecting to Mongo DB.`)
        await connect(3)

        const usersToBackfill = await User.find({ 
            inviteCode: { $exists: false } 
        })
        .select("username")
        .lean()

        activityLogger.info(`Found ${usersToBackfill.length} users to add invite`)

        if (usersToBackfill.length > 0) {
            activityLogger.info(`Starting backfilling invite code.`)

            await Promise.all(
                usersToBackfill.map(async(user) => {
                    try {
                        let inviteCode, inviteCodeExists, attempts = 0
                        do {
                            attempts += 1
                            inviteCode = generateInviteCode()
                            inviteCodeExists = await User.exists({ inviteCode: inviteCode })
                        }
                        while(inviteCodeExists) {
                            await User.updateOne(
                                { _id : user._id },
                                { $set: { inviteCode : inviteCode } }
                            )
                        }
                        
                        activityLogger.info(`Unique invite code found and updated for user: ${user.username} after attempts: ${attempts}`)
                    }
                    catch(error) {
                        activityLogger.info(`Encountered error while updating invite code for user: ${user.username}`, error)
                    }
                })
            )
            console.log(`Ended backfilling.`)
        }
        activityLogger.info(`Disconnecting Database.`)
    }
    catch(error) {
        errorLogger.error(`Error occured while backfilling`,error)
    }
    finally {
        const isDiconnected = await disconnect(3)

        if (!isDiconnected) {
            errorLogger.error(`Mongo Disconnection failed.Explicitly exiting script.`)
            process.exit(1)
        }
    }
}

backFillInviteCode()