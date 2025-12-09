const { createSdkMcpServer, tool } = require("@anthropic-ai/claude-agent-sdk");
const { z } = require("zod");

/**
 * MCP Server Factory - Creates custom MCP servers with tools
 */
class McpServerFactory {
  /**
   * Create a custom MCP server with the UpdateFeatureStatus tool
   * This tool allows Claude Code to safely update feature status without
   * directly modifying the feature_list.json file, preventing race conditions
   * and accidental state restoration.
   */
  createFeatureToolsServer(updateFeatureStatusCallback, projectPath) {
    return createSdkMcpServer({
      name: "automaker-tools",
      version: "1.0.0",
      tools: [
        tool(
          "UpdateFeatureStatus",
          "Update the status of a feature in the feature list. Use this tool instead of directly modifying feature_list.json to safely update feature status.",
          {
            featureId: z.string().describe("The ID of the feature to update"),
            status: z.enum(["backlog", "in_progress", "verified"]).describe("The new status for the feature")
          },
          async (args) => {
            try {
              console.log(`[McpServerFactory] UpdateFeatureStatus tool called: featureId=${args.featureId}, status=${args.status}`);

              // Call the provided callback to update feature status
              await updateFeatureStatusCallback(args.featureId, args.status, projectPath);

              return {
                content: [{
                  type: "text",
                  text: `Successfully updated feature ${args.featureId} to status "${args.status}"`
                }]
              };
            } catch (error) {
              console.error("[McpServerFactory] UpdateFeatureStatus tool error:", error);
              return {
                content: [{
                  type: "text",
                  text: `Failed to update feature status: ${error.message}`
                }]
              };
            }
          }
        )
      ]
    });
  }
}

module.exports = new McpServerFactory();
