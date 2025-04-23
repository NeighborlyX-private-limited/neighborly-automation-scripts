const dotenv = require("dotenv")
const User = require("./UserModel")
const { connect, disconnect } = require("./utils/database")
const { generateInviteCode } = require("./utils/InviteCodeGenerator")

dotenv.config({ path: "./config.env" });

const backFillInviteCode = async() => {
    try {
        console.log(`Connecting to Mongo DB.`)
        const isConnected = await connect(3)

        if(!isConnected) {
            process.exit(1)
        }

        const usersToBackfill = await User.find({ 
            inviteCode: { $exists: false } 
        })
        .select("username")
        .lean()

        console.log(`Found ${usersToBackfill.length} users to add invite code.`)

        if (usersToBackfill.length > 0) {
            console.log(`Starting backfilling invite code.`)

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
                        console.log(`Unique invite code found and updated for user: ${user.username} after attempts: ${attempts}`)
                    }
                    catch(error) {
                        console.log(`Encountered error while updating invite code for user: ${user.username}`)
                        console.log(error)
                    }
                })
            )
            console.log(`Ended backfilling.`)
        }
        console.log(`Disconnecting Database.`)
    }
    catch(error) {
        console.log("An error occured while backfilling", error)
    }
    finally {
        await disconnect(3)
    }
}

backFillInviteCode()