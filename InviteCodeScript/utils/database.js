const { mongoose } = require("mongoose")

const connect = async(retryCount) => {
    try {
        await mongoose.connect(process.env.DB_URI)
        console.log("Mongo DB connected successfully.")
        return true
    }
    catch(error) {
        console.log("An error occured: ",error)
        if (retryCount > 0) {
            console.log("Re-trying to connect.")
            return await connect(retryCount - 1)
        }
        else {
            console.log("Connection failed! Retry limit exceeded.")
            return false
        }
    }
}

const disconnect = async(retryCount) => {
    try {
        await mongoose.disconnect()
        console.log("All connection to Mongo DB are successfully closed.")
    }
    catch(error) {
        console.log("An error occured: ",error)
        if (retryCount > 0) {
            console.log("Re-trying to Disconnect.")
            await connect(retryCount - 1)
        }
        else {
            console.log("Failed to Disconnect! Retry limit exceeded.")
        }
    }
}

module.exports = {
    connect, disconnect
}