const path = require("path");
const fs = require("fs/promises");

/**
 * Feature Loader - Handles loading and selecting features from feature_list.json
 */
class FeatureLoader {
  /**
   * Load features from .automaker/feature_list.json
   */
  async loadFeatures(projectPath) {
    const featuresPath = path.join(
      projectPath,
      ".automaker",
      "feature_list.json"
    );

    try {
      const content = await fs.readFile(featuresPath, "utf-8");
      const features = JSON.parse(content);

      // Ensure each feature has an ID
      return features.map((f, index) => ({
        ...f,
        id: f.id || `feature-${index}-${Date.now()}`,
      }));
    } catch (error) {
      console.error("[FeatureLoader] Failed to load features:", error);
      return [];
    }
  }

  /**
   * Update feature status in .automaker/feature_list.json
   */
  async updateFeatureStatus(featureId, status, projectPath) {
    const features = await this.loadFeatures(projectPath);
    const feature = features.find((f) => f.id === featureId);

    if (!feature) {
      console.error(`[FeatureLoader] Feature ${featureId} not found`);
      return;
    }

    // Update the status field
    feature.status = status;

    // Save back to file
    const featuresPath = path.join(
      projectPath,
      ".automaker",
      "feature_list.json"
    );
    const toSave = features.map((f) => ({
      id: f.id,
      category: f.category,
      description: f.description,
      steps: f.steps,
      status: f.status,
    }));

    await fs.writeFile(featuresPath, JSON.stringify(toSave, null, 2), "utf-8");
    console.log(`[FeatureLoader] Updated feature ${featureId}: status=${status}`);
  }

  /**
   * Select the next feature to implement
   * Prioritizes: earlier features in the list that are not verified
   */
  selectNextFeature(features) {
    // Find first feature that is in backlog or in_progress status
    return features.find((f) => f.status !== "verified");
  }
}

module.exports = new FeatureLoader();
