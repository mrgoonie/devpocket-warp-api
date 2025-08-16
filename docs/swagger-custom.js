/**
 * DevPocket API Documentation Custom JavaScript
 * Enhances Swagger UI with custom functionality and branding
 */

(function() {
  'use strict';

  // Wait for Swagger UI to load
  function waitForSwaggerUI(callback) {
    if (window.SwaggerUIBundle) {
      callback();
    } else {
      setTimeout(() => waitForSwaggerUI(callback), 100);
    }
  }

  // Initialize custom functionality
  waitForSwaggerUI(() => {
    console.log('🚀 DevPocket API Documentation loaded');
    
    // Add custom branding and features
    addCustomBranding();
    addSubscriptionTierBadges();
    addBYOKIndicators();
    addWebSocketDocumentation();
    addAuthenticationHelpers();
    addCopyCodeButtons();
    addAPITesting();
    
    // Set up event listeners
    setupEventListeners();
  });

  /**
   * Add DevPocket branding elements
   */
  function addCustomBranding() {
    // Add custom header content
    const infoElement = document.querySelector('.swagger-ui .info');
    if (infoElement) {
      // Add DevPocket logo and links
      const brandingHTML = `
        <div class="devpocket-branding" style="margin-bottom: 20px; padding: 16px; background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%); border-radius: 8px; color: white;">
          <h2 style="margin: 0 0 8px 0; color: white;">🚀 DevPocket API</h2>
          <p style="margin: 0; opacity: 0.9;">AI-Powered Mobile Terminal Backend API</p>
          <div style="margin-top: 12px;">
            <a href="https://devpocket.app" target="_blank" style="color: white; text-decoration: none; margin-right: 16px;">🌐 Website</a>
            <a href="https://github.com/devpocket" target="_blank" style="color: white; text-decoration: none; margin-right: 16px;">📱 GitHub</a>
            <a href="mailto:support@devpocket.app" style="color: white; text-decoration: none;">📧 Support</a>
          </div>
        </div>
      `;
      infoElement.insertAdjacentHTML('afterbegin', brandingHTML);
    }

    // Add footer
    const swaggerContainer = document.querySelector('.swagger-ui .wrapper');
    if (swaggerContainer) {
      const footerHTML = `
        <div class="api-footer">
          <p>Built with ❤️ by the DevPocket Team | 
            <a href="https://devpocket.app/privacy" target="_blank">Privacy Policy</a> | 
            <a href="https://devpocket.app/terms" target="_blank">Terms of Service</a> | 
            <a href="https://devpocket.app/docs" target="_blank">Documentation</a>
          </p>
          <p style="margin-top: 8px; font-size: 12px; opacity: 0.7;">
            API Version: v1.0.0 | Last Updated: ${new Date().toLocaleDateString()}
          </p>
        </div>
      `;
      swaggerContainer.insertAdjacentHTML('beforeend', footerHTML);
    }
  }

  /**
   * Add subscription tier badges to endpoints
   */
  function addSubscriptionTierBadges() {
    // Map endpoints to subscription tiers
    const tierMapping = {
      '/api/auth': 'free',
      '/api/ai': 'free', // BYOK model
      '/api/sessions': 'free',
      '/api/ssh': 'free',
      '/api/commands': 'free',
      '/api/sync': 'pro',
      '/api/profile/subscription': 'pro',
      '/ws/terminal': 'free'
    };

    // Add badges to operation summaries
    setTimeout(() => {
      document.querySelectorAll('.opblock-summary-path').forEach(pathElement => {
        const path = pathElement.textContent.trim();
        let tier = 'free';
        
        // Determine tier based on path
        for (const [pathPrefix, pathTier] of Object.entries(tierMapping)) {
          if (path.startsWith(pathPrefix)) {
            tier = pathTier;
            break;
          }
        }

        // Add tier badge
        const badge = document.createElement('span');
        badge.className = `tier-badge ${tier}`;
        badge.textContent = tier.toUpperCase();
        badge.title = `Available in ${tier.charAt(0).toUpperCase() + tier.slice(1)} tier and above`;
        
        pathElement.parentNode.appendChild(badge);
      });
    }, 1000);
  }

  /**
   * Add BYOK (Bring Your Own Key) indicators to AI endpoints
   */
  function addBYOKIndicators() {
    setTimeout(() => {
      document.querySelectorAll('.opblock-summary-path').forEach(pathElement => {
        const path = pathElement.textContent.trim();
        
        if (path.startsWith('/api/ai')) {
          const indicator = document.createElement('span');
          indicator.className = 'byok-indicator';
          indicator.textContent = 'BYOK';
          indicator.title = 'Bring Your Own Key - Uses your OpenRouter API key';
          
          pathElement.parentNode.appendChild(indicator);
        }
      });
    }, 1000);
  }

  /**
   * Add enhanced WebSocket documentation
   */
  function addWebSocketDocumentation() {
    setTimeout(() => {
      const wsOperation = document.querySelector('[data-path="/ws/terminal"]');
      if (wsOperation) {
        const protocolDoc = document.createElement('div');
        protocolDoc.className = 'websocket-protocol';
        protocolDoc.innerHTML = `
          <h4>📡 WebSocket Protocol Examples</h4>
          <div style="margin-bottom: 16px;">
            <strong>Connection:</strong>
            <pre>ws://localhost:8000/ws/terminal?token=YOUR_JWT_TOKEN&device_id=device123</pre>
          </div>
          
          <div style="margin-bottom: 16px;">
            <strong>Connect to SSH Server:</strong>
            <pre>{
  "type": "connect",
  "data": {
    "session_type": "ssh",
    "ssh_profile_id": "123e4567-e89b-12d3-a456-426614174000",
    "terminal_size": {"rows": 24, "cols": 80}
  }
}</pre>
          </div>
          
          <div style="margin-bottom: 16px;">
            <strong>Send Terminal Input:</strong>
            <pre>{
  "type": "input",
  "session_id": "session-uuid",
  "data": "ls -la\\n",
  "timestamp": "2023-01-01T12:00:00Z"
}</pre>
          </div>
          
          <div>
            <strong>Receive Terminal Output:</strong>
            <pre>{
  "type": "output",
  "session_id": "session-uuid",
  "data": "total 12\\ndrwxr-xr-x 3 user user 4096 Jan  1 12:00 .",
  "timestamp": "2023-01-01T12:00:00Z"
}</pre>
          </div>
        `;
        
        const description = wsOperation.querySelector('.opblock-description');
        if (description) {
          description.appendChild(protocolDoc);
        }
      }
    }, 1500);
  }

  /**
   * Add authentication helpers
   */
  function addAuthenticationHelpers() {
    // Add JWT decoder helper
    setTimeout(() => {
      const authSection = document.querySelector('.auth-wrapper');
      if (authSection) {
        const helperHTML = `
          <div style="margin-top: 16px; padding: 12px; background-color: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
            <h4 style="margin: 0 0 8px 0; color: #333;">🔑 Authentication Helper</h4>
            <p style="margin: 0 0 8px 0; font-size: 14px; color: #666;">
              Enter your JWT token below to automatically authenticate all requests:
            </p>
            <div style="display: flex; gap: 8px; align-items: center;">
              <input type="text" id="jwt-helper" placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." 
                     style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; font-size: 12px;">
              <button id="apply-jwt" style="padding: 8px 16px; background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Apply
              </button>
              <button id="clear-jwt" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Clear
              </button>
            </div>
            <p style="margin: 8px 0 0 0; font-size: 12px; color: #666;">
              💡 Tip: Get your token from <code>POST /api/auth/login</code> or <code>POST /api/auth/register</code>
            </p>
          </div>
        `;
        authSection.insertAdjacentHTML('beforeend', helperHTML);

        // Set up JWT helper functionality
        document.getElementById('apply-jwt').addEventListener('click', () => {
          const token = document.getElementById('jwt-helper').value.trim();
          if (token) {
            // Set authorization for Swagger UI
            window.ui.preauthorizeApiKey('bearerAuth', `Bearer ${token}`);
            showNotification('✅ JWT token applied successfully!', 'success');
          } else {
            showNotification('❌ Please enter a valid JWT token', 'error');
          }
        });

        document.getElementById('clear-jwt').addEventListener('click', () => {
          document.getElementById('jwt-helper').value = '';
          window.ui.preauthorizeApiKey('bearerAuth', '');
          showNotification('🗑️ JWT token cleared', 'info');
        });
      }
    }, 2000);
  }

  /**
   * Add copy code buttons to code blocks
   */
  function addCopyCodeButtons() {
    const addCopyButton = (codeBlock) => {
      if (codeBlock.querySelector('.copy-button')) return; // Already added

      const button = document.createElement('button');
      button.className = 'copy-button';
      button.textContent = '📋 Copy';
      button.style.cssText = `
        position: absolute;
        top: 8px;
        right: 8px;
        padding: 4px 8px;
        background: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 12px;
        cursor: pointer;
        opacity: 0.8;
        transition: opacity 0.2s;
      `;

      button.addEventListener('click', () => {
        const code = codeBlock.textContent;
        navigator.clipboard.writeText(code).then(() => {
          button.textContent = '✅ Copied!';
          setTimeout(() => {
            button.textContent = '📋 Copy';
          }, 2000);
        });
      });

      codeBlock.style.position = 'relative';
      codeBlock.appendChild(button);
    };

    // Add copy buttons to existing code blocks
    const observer = new MutationObserver(() => {
      document.querySelectorAll('.highlight-code, pre').forEach(addCopyButton);
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  /**
   * Add API testing enhancements
   */
  function addAPITesting() {
    // Add quick test scenarios
    setTimeout(() => {
      const infoElement = document.querySelector('.swagger-ui .info');
      if (infoElement) {
        const testingHTML = `
          <div style="margin-top: 24px; padding: 16px; background-color: #e8f5e8; border: 1px solid #c3e6c3; border-radius: 8px;">
            <h3 style="margin: 0 0 12px 0; color: #2d5a2d;">🧪 Quick Test Scenarios</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
              <button class="test-scenario" data-scenario="auth" style="padding: 12px; background: white; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; text-align: left;">
                <strong>🔐 Authentication Flow</strong><br>
                <small>Register → Login → Get Profile</small>
              </button>
              <button class="test-scenario" data-scenario="ssh" style="padding: 12px; background: white; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; text-align: left;">
                <strong>🖥️ SSH Management</strong><br>
                <small>Create Profile → Test Connection</small>
              </button>
              <button class="test-scenario" data-scenario="ai" style="padding: 12px; background: white; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; text-align: left;">
                <strong>🤖 AI Services (BYOK)</strong><br>
                <small>Validate Key → Get Suggestions</small>
              </button>
            </div>
          </div>
        `;
        infoElement.insertAdjacentHTML('beforeend', testingHTML);

        // Set up test scenario handlers
        document.querySelectorAll('.test-scenario').forEach(button => {
          button.addEventListener('click', (e) => {
            const scenario = e.currentTarget.dataset.scenario;
            showTestScenario(scenario);
          });
        });
      }
    }, 2500);
  }

  /**
   * Show test scenario instructions
   */
  function showTestScenario(scenario) {
    const scenarios = {
      auth: {
        title: '🔐 Authentication Flow Test',
        steps: [
          '1. Go to POST /api/auth/register',
          '2. Try it out with test credentials',
          '3. Copy the access_token from response',
          '4. Use "Apply" button in auth helper above',
          '5. Test GET /api/auth/me to verify'
        ]
      },
      ssh: {
        title: '🖥️ SSH Management Test',
        steps: [
          '1. Authenticate first (see Auth Flow)',
          '2. Go to POST /api/ssh/profiles',
          '3. Create a test SSH profile',
          '4. Copy the profile ID from response',
          '5. Test POST /api/ssh/profiles/{id}/test'
        ]
      },
      ai: {
        title: '🤖 AI Services (BYOK) Test',
        steps: [
          '1. Get OpenRouter API key from openrouter.ai',
          '2. Go to POST /api/ai/validate-key',
          '3. Test your API key validation',
          '4. Try POST /api/ai/suggest-command',
          '5. Example: "List all files with details"'
        ]
      }
    };

    const scenario_info = scenarios[scenario];
    if (scenario_info) {
      showNotification(
        `${scenario_info.title}\n\n${scenario_info.steps.join('\n')}`,
        'info',
        8000
      );
    }
  }

  /**
   * Set up event listeners
   */
  function setupEventListeners() {
    // Auto-expand important sections
    setTimeout(() => {
      const importantTags = ['Authentication', 'AI Services', 'WebSocket'];
      document.querySelectorAll('.opblock-tag').forEach(tag => {
        if (importantTags.some(important => tag.textContent.includes(important))) {
          tag.click();
        }
      });
    }, 3000);

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + K to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.swagger-ui .filter input');
        if (searchInput) {
          searchInput.focus();
        }
      }

      // Escape to clear search
      if (e.key === 'Escape') {
        const searchInput = document.querySelector('.swagger-ui .filter input');
        if (searchInput && document.activeElement === searchInput) {
          searchInput.value = '';
          searchInput.blur();
        }
      }
    });
  }

  /**
   * Show notification to user
   */
  function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 16px 20px;
      background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
      color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
      border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
      border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 10000;
      max-width: 400px;
      white-space: pre-line;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.4;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Auto-remove notification
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, duration);

    // Click to dismiss
    notification.addEventListener('click', () => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    });
  }

  /**
   * Add environment selector
   */
  function addEnvironmentSelector() {
    const environments = {
      development: 'http://localhost:8000',
      staging: 'https://staging-api.devpocket.app',
      production: 'https://api.devpocket.app'
    };

    const selectorHTML = `
      <div style="margin: 16px 0; padding: 12px; background-color: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
        <label for="env-selector" style="display: block; margin-bottom: 8px; font-weight: 600; color: #333;">
          🌍 Environment:
        </label>
        <select id="env-selector" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
          ${Object.entries(environments).map(([name, url]) => 
            `<option value="${url}">${name.charAt(0).toUpperCase() + name.slice(1)} (${url})</option>`
          ).join('')}
        </select>
      </div>
    `;

    setTimeout(() => {
      const schemeContainer = document.querySelector('.scheme-container');
      if (schemeContainer) {
        schemeContainer.insertAdjacentHTML('afterend', selectorHTML);

        document.getElementById('env-selector').addEventListener('change', (e) => {
          const newUrl = e.target.value;
          if (window.ui && window.ui.specActions) {
            window.ui.specActions.updateUrl(newUrl);
            showNotification(`🔄 Environment changed to: ${newUrl}`, 'success');
          }
        });
      }
    }, 2000);
  }

  // Initialize environment selector
  addEnvironmentSelector();

  // Add global helper functions
  window.DevPocketAPI = {
    showNotification,
    showTestScenario,
    environments: {
      dev: 'http://localhost:8000',
      staging: 'https://staging-api.devpocket.app',
      prod: 'https://api.devpocket.app'
    }
  };

  console.log('✅ DevPocket API Documentation enhancements loaded');
})();