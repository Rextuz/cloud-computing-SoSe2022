const UserProfileFiles = require("../db/model/UserProfileFiles");
const { Sequelize } = require("sequelize");
const Op = Sequelize.Op;

//************* Get List of All profiles based on userId" ***************

const getallbyuserid = async (req, res, next) => {
    const userprofilefiles = await UserProfileFiles.findAll({
        where: { userId: req.params.userId },
    });

    res.json({
        success: true,
        message: "User Porofile Files",
        records: userprofilefiles.length,
        data: userprofilefiles,
    });
};

exports.getallbyuserid = getallbyuserid;

//************* Get specific profile file based on file id(id) " ***************

const getallbyfileid = async (req, res, next) => {
    const userprofilefiles = await UserProfileFiles.findOne({
        where: { id: req.params.fileId },
    });

    res.json({
        success: true,
        message: "User Porofile File",
        records: userprofilefiles.length,
        data: userprofilefiles,
    });
};

exports.getallbyfileid = getallbyfileid;

//************* Get all profile file based on file approval status " ***************

const getallbystatus = async (req, res, next) => {
    const userprofilefiles = await UserProfileFiles.findAll({
        where: { approvalStatus: req.params.approvalStatus },
    });

    res.json({
        success: true,
        message: "User Porofile Files",
        records: userprofilefiles.length,
        data: userprofilefiles,
    });
};

exports.getallbystatus = getallbystatus;

//************* Get all profile file based on user id and file approval status " ***************

const getallbyuserfilestatus = async (req, res, next) => {
    const userprofilefiles = await UserProfileFiles.findAll({
        where: {
            userId: req.params.userId,
            approvalStatus: req.params.approvalStatus,
        },
    });

    res.json({
        success: true,
        message: "User Porofile File",
        records: userprofilefiles.length,
        data: userprofilefiles,
    });
};

exports.getallbyuserfilestatus = getallbyuserfilestatus;

//************* Create User profile file ***************

const createuserprofilefile = async (req, res, next) => {
    let profilefile = UserProfileFiles.build({
        userId: req.body.userId,
        fileTitle: req.body.fileTitle,
        filePath: req.body.filePath,
        approvalStatus: "PendingApproval",
    });

    await profilefile.save().catch((e) => {
        console.log(e);
    });

    res.json({
        success: true,
        message: "Profile File Successfully Saved",
        records: profilefile.length,
        data: profilefile,
    });
};

exports.createuserprofilefile = createuserprofilefile;

//************* Update Existing profile file ***************

const updateuserprofilefile = async (req, res, next) => {
    const userprofilefile = await UserProfileFiles.findOne({
        where: { id: req.params.fileId },
    });

    if (userprofilefile) {
        try {
            await userprofilefile.update({
                userId: req.body.userId,
                fileTitle: req.body.fileTitle,
                filePath: req.body.filePath,
                approvalStatus: req.body.approvalStatus,
            });
            res.json({
                success: true,
                message:
                    "User Profile File '" +
                    userprofilefile.userId +
                    "' successfully updated",
                records: userprofilefile.length,
            });
        } catch (e) {
            res.json({
                success: false,
                message:
                    "User Profile File " +
                    userprofilefile.userId +
                    " updation failed",
                records: userprofilefile.length,
            });
        }
    } else {
        res.json({
            success: false,
            message:
                "Provided user profile file id doesn't exist or is already deleted",
        });
    }
};

exports.updateuserprofilefile = updateuserprofilefile;

//************* Delete Existing user profile file ***************

const deleteuserprofilefile = async (req, res, next) => {
    const userprofilefile = await UserProfileFiles.findOne({
        where: { id: req.params.fileId },
    });

    if (userprofilefile) {
        try {
            await userprofilefile.destroy();
            res.json({
                success: true,
                message:
                    "User profile file '" +
                    userprofilefile.id +
                    "' successfully deleted",
                records: userprofilefile.length,
            });
        } catch (e) {
            res.json({
                success: false,
                message:
                    "User profile file " +
                    userprofilefile.id +
                    " deletion failed",
                records: userprofilefile.length,
            });
        }
    } else {
        res.json({
            success: false,
            message:
                "Provided user profile file doesn't exist or is already deleted",
        });
    }
};

exports.deleteuserprofilefile = deleteuserprofilefile;
