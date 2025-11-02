module.exports = {
    apps: [
      {
        name: "smart-mahalla-bot",
        script: "./bot.py",
        interpreter: "python3",
        watch: true
      },
      {
        name: "smart-mahalla-admin",
        script: "./admin.py",
        interpreter: "python3",
        env: {
          "PORT": 5000
        },
        watch: true
      }
    ]
  }