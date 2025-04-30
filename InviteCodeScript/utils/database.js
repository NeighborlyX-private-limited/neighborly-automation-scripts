const { mongoose } = require("mongoose")
const { activityLogger, errorLogger } = require("./logger")
const { Pool } = require("pg")

const connect = async(retryCount) => {
    try {
        await mongoose.connect(process.env.DB_URI)
        activityLogger.info(`Mongo DB connected successfully.`)
    }
    catch(error) {
        activityLogger.info(`Error occured while connecting to Mongo DB: `)
        if (retryCount > 0) {
            activityLogger.info(`Re-trying to connect.`)
            return await connect(retryCount - 1)
        }
        return error
    }
}

const disconnect = async(retryCount) => {
    try {
        await mongoose.disconnect()
        activityLogger.info(`All connection to Mongo DB are successfully disconneted.`)
        return true
    }
    catch(error) {
        activityLogger.info(`Error occured while disconnecting to Mongo DB: `)
        if (retryCount > 0) {
            activityLogger.info(`Re-trying to disconnect.`)
            return await connect(retryCount - 1)
        }
        errorLogger.error(`Error while disconnecting Mongo connection: `,error)
        return false
    }
}

console.log ({
    user: process.env.PG_USERNAME,
    host: process.env.PG_HOSTNAME,
    password: process.env.PG_PASSWORD,
    port: process.env.PG_PORT,
    database: process.env.PG_DATABASE
})

const pool = new Pool({
    user: process.env.PG_USERNAME,
    host: process.env.PG_HOSTNAME,
    password: process.env.PG_PASSWORD,
    port: process.env.PG_PORT,
    database: process.env.PG_DATABASE
})

module.exports = {
    connect, disconnect, pool
}