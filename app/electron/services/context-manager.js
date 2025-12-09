const path = require("path");
const fs = require("fs/promises");

/**
 * Context Manager - Handles reading, writing, and deleting context files for features
 */
class ContextManager {
  /**
   * Write output to feature context file
   */
  async writeToContextFile(projectPath, featureId, content) {
    if (!projectPath) return;

    try {
      const contextDir = path.join(projectPath, ".automaker", "agents-context");

      // Ensure directory exists
      try {
        await fs.access(contextDir);
      } catch {
        await fs.mkdir(contextDir, { recursive: true });
      }

      const filePath = path.join(contextDir, `${featureId}.md`);

      // Append to existing file or create new one
      try {
        const existing = await fs.readFile(filePath, "utf-8");
        await fs.writeFile(filePath, existing + content, "utf-8");
      } catch {
        await fs.writeFile(filePath, content, "utf-8");
      }
    } catch (error) {
      console.error("[ContextManager] Failed to write to context file:", error);
    }
  }

  /**
   * Read context file for a feature
   */
  async readContextFile(projectPath, featureId) {
    try {
      const contextPath = path.join(projectPath, ".automaker", "agents-context", `${featureId}.md`);
      const content = await fs.readFile(contextPath, "utf-8");
      return content;
    } catch (error) {
      console.log(`[ContextManager] No context file found for ${featureId}`);
      return null;
    }
  }

  /**
   * Delete agent context file for a feature
   */
  async deleteContextFile(projectPath, featureId) {
    if (!projectPath) return;

    try {
      const contextPath = path.join(projectPath, ".automaker", "agents-context", `${featureId}.md`);
      await fs.unlink(contextPath);
      console.log(`[ContextManager] Deleted agent context for feature ${featureId}`);
    } catch (error) {
      // File might not exist, which is fine
      if (error.code !== 'ENOENT') {
        console.error("[ContextManager] Failed to delete context file:", error);
      }
    }
  }
}

module.exports = new ContextManager();
