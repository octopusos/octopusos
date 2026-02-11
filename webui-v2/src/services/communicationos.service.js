"use strict";
/**
 * CommunicationOS Service
 *
 * API functions for CommunicationOS:
 * - Channels management
 * - Channels marketplace
 * - Communication sessions
 * - Voice/Twilio integration
 * - MCP (Model Context Protocol) servers
 * - MCP marketplace
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.communicationosService = void 0;
var http_1 = require("@platform/http");
var communicationos_service_gen_1 = require("./communicationos.service.gen");
// ============================================================================
// Service Functions
// ============================================================================
exports.communicationosService = {
    // Channels Management
    listChannels: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/channels', { params: params })];
            });
        });
    },
    getChannel: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/channels/".concat(id))];
            });
        });
    },
    createChannel: function (data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)('/api/channels', data)];
            });
        });
    },
    updateChannel: function (id, data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.put)("/api/channels/".concat(id), data)];
            });
        });
    },
    deleteChannel: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.del)("/api/channels/".concat(id))];
            });
        });
    },
    getChannelStatus: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/channels/".concat(id, "/status"))];
            });
        });
    },
    // Channels Marketplace
    listChannelMarketplace: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/channels-marketplace', { params: params })];
            });
        });
    },
    getChannelMarketplaceItem: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/channels-marketplace/".concat(id))];
            });
        });
    },
    getChannelConfig: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/channels-marketplace/".concat(id, "/config"))];
            });
        });
    },
    updateChannelConfig: function (id, data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.put)("/api/channels-marketplace/".concat(id, "/config"), data)];
            });
        });
    },
    enableChannel: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/channels-marketplace/".concat(id, "/enable"))];
            });
        });
    },
    disableChannel: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/channels-marketplace/".concat(id, "/disable"))];
            });
        });
    },
    testChannel: function (id, data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/channels-marketplace/".concat(id, "/test"), data)];
            });
        });
    },
    getChannelEvents: function (id, params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/channels-marketplace/".concat(id, "/events"), { params: params })];
            });
        });
    },
    // Communication Sessions
    listCommunicationSessions: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/communication/sessions', { params: params })];
            });
        });
    },
    getCommunicationSession: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/communication/sessions/".concat(id))];
            });
        });
    },
    // Voice/Twilio Integration
    listVoiceSessions: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/voice/sessions', { params: params })];
            });
        });
    },
    getVoiceSession: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/voice/sessions/".concat(id))];
            });
        });
    },
    startVoiceCall: function (data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)('/api/voice/call', data)];
            });
        });
    },
    endVoiceCall: function (sessionId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/voice/sessions/".concat(sessionId, "/end"))];
            });
        });
    },
    // MCP Servers Management
    listMCPServers: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/mcp/servers')];
            });
        });
    },
    getMCPServer: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/mcp/servers/".concat(id))];
            });
        });
    },
    refreshMCPServers: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)('/api/mcp/servers/refresh')];
            });
        });
    },
    connectMCPServer: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/mcp/servers/".concat(id, "/connect"))];
            });
        });
    },
    disconnectMCPServer: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/mcp/servers/".concat(id, "/disconnect"))];
            });
        });
    },
    preflightMCPServer: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/mcp/servers/".concat(id, "/preflight"))];
            });
        });
    },
    enableMCPServer: function (id, data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/mcp/servers/".concat(id, "/enable"), data)];
            });
        });
    },
    disableMCPServer: function (id) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)("/api/mcp/servers/".concat(id, "/disable"))];
            });
        });
    },
    listLocalAwsProfiles: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/mcp/aws/profiles')];
            });
        });
    },
    // MCP Marketplace
    listMCPMarketplaceCatalog: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/mcp/marketplace/catalog', { params: params })];
            });
        });
    },
    listMCPMarketplace: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/mcp/marketplace/packages', { params: params })];
            });
        });
    },
    getMCPMarketplaceItem: function (packageId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/mcp/marketplace/packages/".concat(packageId))];
            });
        });
    },
    getMCPGovernancePreview: function (packageId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/mcp/marketplace/governance-preview/".concat(packageId))];
            });
        });
    },
    attachMCPPackage: function (data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.post)('/api/mcp/marketplace/attach', data)];
            });
        });
    },
    uninstallMCPPackage: function (packageId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, communicationos_service_gen_1.communicationosServiceGen.uninstallMcpPackageCanonicalApiMcpMarketplacePackagesPackageIdDelete(packageId)];
            });
        });
    },
    // Communication Audit & Control API (CommunicationOS Core)
    getNetworkMode: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/communication/mode')];
            });
        });
    },
    setNetworkMode: function (data) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.put)('/api/communication/mode', data)];
            });
        });
    },
    getCommunicationStatus: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/communication/status')];
            });
        });
    },
    getCommunicationPolicy: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/communication/policy')];
            });
        });
    },
    listCommunicationAudits: function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)('/api/communication/audits', { params: params })];
            });
        });
    },
    getCommunicationAuditDetail: function (auditId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, (0, http_1.get)("/api/communication/audits/".concat(auditId))];
            });
        });
    },
};
