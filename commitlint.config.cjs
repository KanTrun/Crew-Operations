module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "scope-enum": [
      2,
      "always",
      [
        "solver",
        "gates",
        "ops",
        "playbook",
        "api",
        "orc",
        "agents",
        "router",
        "web",
        "tpl",
        "contracts",
        "infra",
      ],
    ],
  },
};
