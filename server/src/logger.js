import chalk from "chalk";

const logger = {
  info: (...msg) => console.log(chalk.blue("[INFO]"), ...msg),
  success: (...msg) => console.log(chalk.green("[SUCCESS]"), ...msg),
  warn: (...msg) => console.log(chalk.yellow("[WARN]"), ...msg),
  error: (...msg) => console.log(chalk.red("[ERROR]"), ...msg),
};

export default logger;  
export { logger };
