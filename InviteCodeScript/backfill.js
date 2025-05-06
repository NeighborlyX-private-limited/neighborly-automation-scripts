const dotenv = require("dotenv")
dotenv.config({ path: "./config.env" }); // Don't change sequence of imports
const { connect, disconnect, pool } = require("./utils/database")
const User = require("./UserModel")
const { generateCode } = require("./utils/CodeGenerator")
const { activityLogger, errorLogger } = require("./utils/logger")


const backFillInviteCode = async() => {
    try {
        activityLogger.info(`Connecting to Mongo DB.`)
        await connect(3)

        const usersToBackfill = await User.find({ 
            isDeleted: false
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
                            inviteCode = generateCode()
                            inviteCodeExists = await User.exists({ inviteCode: inviteCode })
                        }
                        while(inviteCodeExists) {
                            await User.updateOne(
                                { _id : user._id },
                                { $set: { inviteCode : inviteCode } }
                            )
                                
                            await pool.query(
                                `INSERT INTO referrals (
                                referee_user_id,
                                referee_reward_eligibility,
                                "createdAt",
                                "updatedAt"
                                )
                                VALUES ($1, $2, $3, $4);`, 
                                [user._id.toString(), false, new Date(), new Date()]
                            )
                        }
                        
                        activityLogger.info(`Unique invite code found and updated for user: ${user.username} after attempts: ${attempts}`)
                    }
                    catch(error) {
                        activityLogger.info(`Encountered error while updating invite code for user: ${user.username}`, error)
                    }
                })
            )
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