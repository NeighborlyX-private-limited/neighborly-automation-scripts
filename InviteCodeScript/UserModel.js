const mongoose = require("mongoose");

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: [true, "Please enter username"],
    unique: true,
    sparse: true,
  },
  password: {
    type: String,
  },
  picture: {
    type: String,
  },
  gender: {
    type: String,
  },
  dob: {
    type: Date,
  },
  email: {
    type: String,
    unique: true,
    sparse: true, // Allow multiple null values
  },
  phoneNumber: {
    type: String,
    unique: true,
    sparse: true, // Allow multiple null values
  },
  current_coordinates: {
    type: {
      type: String,
      enum: ["Point"],
      default: "Point",
    },
    coordinates: {
      type: [Number],
      default: [28.5643, 77.2442],
    },
  },
  home_coordinates: {
    type: {
      type: String,
      enum: ["Point"],
      default: "Point",
    },
    coordinates: {
      type: [Number],
      default: [28.5643, 77.2442],
    },
  },
  findMe: {
    type: Boolean,
    default: true,
  },
  groups: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Group",
    },
  ],
  mutedGroups: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Group",
    },
  ],
  karma: {
    type: Number,
    default: 0,
  },
  auth_type: {
    type: String,
    required: true,
    enum: ["email", "phone", "google"],
  },
  isVerified: {
    type: Boolean,
    default: false,
  },
  otp: {
    type: String,
  },
  otpExpiry: {
    type: Date,
  },
  bio: {
    type: String,
  },
  isDeleted: {
    type: Boolean,
    default: false,
  },
  dobSet: {
    type: Boolean,
    default: false,
    required: true,
  },
  isPhoneVerified: {
    type: Boolean,
    default: false,
  },
  awards: {
    type: Object,
    default: {
      "Local Legend": 2,
      Sunflower: 2,
      Streetlight: 2,
      "Park Bench": 2,
      Map: 2,
    },
  },
  fcmToken: {
    type: String,
    required: true,
  },
  refreshToken: {
    type: String,
    required: false,
  },
  isBanned: {
    type: Boolean,
    default: false,
  },
  bannedExpiry: {
    type: Date,
  },
  viewedTutorial: {
    type: Boolean,
    default: false,
  },
  skippedTutorial: {
    type: Boolean,
    default: false,
  },
  isAdmin: {
    type: Boolean,
    default: false,
    sparse: true, // Allow multiple null values
  },
  joinDate: {
    type: Date,
    default: Date.now,
  },
  interests : [ 
    { type : String, default : [], unique : true } 
  ],
  createdAt: {
    type: Date,
    default: Date.now,
  },
  inviteCode : {
    type : String,
    required : true,
    unique : true,
    validate: {
      validator: function(v) {
        return v && v.length === 8;
      },
      message: props => `${props.value} must be exactly 8 characters!`
    }
  }
});

// Add 2dsphere index on current_coordinates
userSchema.index({ current_coordinates: "2dsphere" });
userSchema.index({ city: "2dsphere" });

module.exports = mongoose.model("User", userSchema);
