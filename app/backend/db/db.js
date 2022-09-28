const { Sequelize } = require("sequelize");

module.exports = new Sequelize("db", "mysqluser", "attic-humorous-stylishly", {
    host: "DATABASE_IP",
    port: 3306,
    dialect: "mysql",
});
