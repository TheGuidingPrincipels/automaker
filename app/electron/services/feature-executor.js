const { query, AbortError } = require("@anthropic-ai/claude-agent-sdk");
const promptBuilder = require("./prompt-builder");
const contextManager = require("./context-manager");
const featureLoader = require("./feature-loader");
const mcpServerFactory = require("./mcp-server-factory");

/**
 * Feature Executor - Handles feature implementation using Claude Agent SDK
 */
class FeatureExecutor {
  /**
   * Sleep helper
   */
  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Implement a single feature using Claude Agent SDK
   * Uses a Plan-Act-Verify loop with detailed phase logging
   */
  async implementFeature(feature, projectPath, sendToRenderer, execution) {
    console.log(`[FeatureExecutor] Implementing: ${feature.description}`);

    try {
      // ========================================
      // PHASE 1: PLANNING
      // ========================================
      const planningMessage = `📋 Planning implementation for: ${feature.description}\n`;
      await contextManager.writeToContextFile(projectPath, feature.id, planningMessage);

      sendToRenderer({
        type: "auto_mode_phase",
        featureId: feature.id,
        phase: "planning",
        message: `Planning implementation for: ${feature.description}`,
      });
      console.log(`[FeatureExecutor] Phase: PLANNING for ${feature.description}`);

      const abortController = new AbortController();
      execution.abortController = abortController;

      // Create custom MCP server with UpdateFeatureStatus tool
      const featureToolsServer = mcpServerFactory.createFeatureToolsServer(
        featureLoader.updateFeatureStatus.bind(featureLoader),
        projectPath
      );

      // Configure options for the SDK query
      const options = {
        model: "claude-opus-4-5-20251101",
        systemPrompt: promptBuilder.getCodingPrompt(),
        maxTurns: 1000,
        cwd: projectPath,
        mcpServers: {
          "automaker-tools": featureToolsServer
        },
        allowedTools: [
          "Read",
          "Write",
          "Edit",
          "Glob",
          "Grep",
          "Bash",
          "WebSearch",
          "WebFetch",
          "mcp__automaker-tools__UpdateFeatureStatus",
        ],
        permissionMode: "acceptEdits",
        sandbox: {
          enabled: true,
          autoAllowBashIfSandboxed: true,
        },
        abortController: abortController,
      };

      // Build the prompt for this specific feature
      const prompt = promptBuilder.buildFeaturePrompt(feature);

      // Planning: Analyze the codebase and create implementation plan
      sendToRenderer({
        type: "auto_mode_progress",
        featureId: feature.id,
        content:
          "Analyzing codebase structure and creating implementation plan...",
      });

      // Small delay to show planning phase
      await this.sleep(500);

      // ========================================
      // PHASE 2: ACTION
      // ========================================
      const actionMessage = `⚡ Executing implementation for: ${feature.description}\n`;
      await contextManager.writeToContextFile(projectPath, feature.id, actionMessage);

      sendToRenderer({
        type: "auto_mode_phase",
        featureId: feature.id,
        phase: "action",
        message: `Executing implementation for: ${feature.description}`,
      });
      console.log(`[FeatureExecutor] Phase: ACTION for ${feature.description}`);

      // Send query
      const currentQuery = query({ prompt, options });
      execution.query = currentQuery;

      // Stream responses
      let responseText = "";
      let hasStartedToolUse = false;
      for await (const msg of currentQuery) {
        // Check if this specific feature was aborted
        if (!execution.isActive()) break;

        if (msg.type === "assistant" && msg.message?.content) {
          for (const block of msg.message.content) {
            if (block.type === "text") {
              responseText += block.text;

              // Write to context file
              await contextManager.writeToContextFile(projectPath, feature.id, block.text);

              // Stream progress to renderer
              sendToRenderer({
                type: "auto_mode_progress",
                featureId: feature.id,
                content: block.text,
              });
            } else if (block.type === "tool_use") {
              // First tool use indicates we're actively implementing
              if (!hasStartedToolUse) {
                hasStartedToolUse = true;
                const startMsg = "Starting code implementation...\n";
                await contextManager.writeToContextFile(projectPath, feature.id, startMsg);
                sendToRenderer({
                  type: "auto_mode_progress",
                  featureId: feature.id,
                  content: startMsg,
                });
              }

              // Write tool use to context file
              const toolMsg = `\n🔧 Tool: ${block.name}\n`;
              await contextManager.writeToContextFile(projectPath, feature.id, toolMsg);

              // Notify about tool use
              sendToRenderer({
                type: "auto_mode_tool",
                featureId: feature.id,
                tool: block.name,
                input: block.input,
              });
            }
          }
        }
      }

      execution.query = null;
      execution.abortController = null;

      // ========================================
      // PHASE 3: VERIFICATION
      // ========================================
      const verificationMessage = `✅ Verifying implementation for: ${feature.description}\n`;
      await contextManager.writeToContextFile(projectPath, feature.id, verificationMessage);

      sendToRenderer({
        type: "auto_mode_phase",
        featureId: feature.id,
        phase: "verification",
        message: `Verifying implementation for: ${feature.description}`,
      });
      console.log(`[FeatureExecutor] Phase: VERIFICATION for ${feature.description}`);

      const checkingMsg =
        "Verifying implementation and checking test results...\n";
      await contextManager.writeToContextFile(projectPath, feature.id, checkingMsg);
      sendToRenderer({
        type: "auto_mode_progress",
        featureId: feature.id,
        content: checkingMsg,
      });

      // Re-load features to check if it was marked as verified
      const updatedFeatures = await featureLoader.loadFeatures(projectPath);
      const updatedFeature = updatedFeatures.find((f) => f.id === feature.id);
      const passes = updatedFeature?.status === "verified";

      // Send verification result
      const resultMsg = passes
        ? "✓ Verification successful: All tests passed\n"
        : "✗ Verification: Tests need attention\n";

      await contextManager.writeToContextFile(projectPath, feature.id, resultMsg);
      sendToRenderer({
        type: "auto_mode_progress",
        featureId: feature.id,
        content: resultMsg,
      });

      return {
        passes,
        message: responseText.substring(0, 500), // First 500 chars
      };
    } catch (error) {
      if (error instanceof AbortError || error?.name === "AbortError") {
        console.log("[FeatureExecutor] Feature run aborted");
        if (execution) {
          execution.abortController = null;
          execution.query = null;
        }
        return {
          passes: false,
          message: "Auto mode aborted",
        };
      }

      console.error("[FeatureExecutor] Error implementing feature:", error);

      // Clean up
      if (execution) {
        execution.abortController = null;
        execution.query = null;
      }

      throw error;
    }
  }

  /**
   * Resume feature implementation with previous context
   */
  async resumeFeatureWithContext(feature, projectPath, sendToRenderer, previousContext, execution) {
    console.log(`[FeatureExecutor] Resuming with context for: ${feature.description}`);

    try {
      const resumeMessage = `\n🔄 Resuming implementation for: ${feature.description}\n`;
      await contextManager.writeToContextFile(projectPath, feature.id, resumeMessage);

      sendToRenderer({
        type: "auto_mode_phase",
        featureId: feature.id,
        phase: "action",
        message: `Resuming implementation for: ${feature.description}`,
      });

      const abortController = new AbortController();
      execution.abortController = abortController;

      // Create custom MCP server with UpdateFeatureStatus tool
      const featureToolsServer = mcpServerFactory.createFeatureToolsServer(
        featureLoader.updateFeatureStatus.bind(featureLoader),
        projectPath
      );

      const options = {
        model: "claude-opus-4-5-20251101",
        systemPrompt: promptBuilder.getVerificationPrompt(),
        maxTurns: 1000,
        cwd: projectPath,
        mcpServers: {
          "automaker-tools": featureToolsServer
        },
        allowedTools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch", "mcp__automaker-tools__UpdateFeatureStatus"],
        permissionMode: "acceptEdits",
        sandbox: {
          enabled: true,
          autoAllowBashIfSandboxed: true,
        },
        abortController: abortController,
      };

      // Build prompt with previous context
      const prompt = promptBuilder.buildResumePrompt(feature, previousContext);

      const currentQuery = query({ prompt, options });
      execution.query = currentQuery;

      let responseText = "";
      for await (const msg of currentQuery) {
        // Check if this specific feature was aborted
        if (!execution.isActive()) break;

        if (msg.type === "assistant" && msg.message?.content) {
          for (const block of msg.message.content) {
            if (block.type === "text") {
              responseText += block.text;

              await contextManager.writeToContextFile(projectPath, feature.id, block.text);

              sendToRenderer({
                type: "auto_mode_progress",
                featureId: feature.id,
                content: block.text,
              });
            } else if (block.type === "tool_use") {
              const toolMsg = `\n🔧 Tool: ${block.name}\n`;
              await contextManager.writeToContextFile(projectPath, feature.id, toolMsg);

              sendToRenderer({
                type: "auto_mode_tool",
                featureId: feature.id,
                tool: block.name,
                input: block.input,
              });
            }
          }
        }
      }

      execution.query = null;
      execution.abortController = null;

      // Check if feature was marked as verified
      const updatedFeatures = await featureLoader.loadFeatures(projectPath);
      const updatedFeature = updatedFeatures.find((f) => f.id === feature.id);
      const passes = updatedFeature?.status === "verified";

      const finalMsg = passes
        ? "✓ Feature successfully verified and completed\n"
        : "⚠ Feature still in progress - may need additional work\n";

      await contextManager.writeToContextFile(projectPath, feature.id, finalMsg);

      sendToRenderer({
        type: "auto_mode_progress",
        featureId: feature.id,
        content: finalMsg,
      });

      return {
        passes,
        message: responseText.substring(0, 500),
      };
    } catch (error) {
      if (error instanceof AbortError || error?.name === "AbortError") {
        console.log("[FeatureExecutor] Resume aborted");
        if (execution) {
          execution.abortController = null;
          execution.query = null;
        }
        return {
          passes: false,
          message: "Resume aborted",
        };
      }

      console.error("[FeatureExecutor] Error resuming feature:", error);
      if (execution) {
        execution.abortController = null;
        execution.query = null;
      }
      throw error;
    }
  }
}

module.exports = new FeatureExecutor();
