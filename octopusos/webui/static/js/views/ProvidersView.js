/* Providers View */

class ProvidersView {
  constructor(apiClient) {
    this.apiClient = apiClient;
  }

  // Task #22: P0.4补充 - 添加 refresh 端点
  async refreshStatus() {
    try {
      await this.apiClient.post('/providers/refresh');
      setTimeout(async () => {
        await this.loadInstances();
      }, 1000);
    } catch (err) {
      Toast.error('Failed to refresh status');
    }
  }

  async loadInstances() {
    // Placeholder for actual implementation.
  }
}

export default ProvidersView;
