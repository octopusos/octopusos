/**
 * McpMarketplacePage - MCP Marketplace
 *
 * 🔒 Migration Contract 遵循规则：
 * - ✅ Text System: 使用 t(K.xxx)（G7-G8）
 * - ✅ Layout: usePageHeader + usePageActions（G10-G11）
 * - ✅ CardGrid Pattern: CardCollectionWrap + ItemCard
 * - ✅ API Integration: listMCPMarketplace + DetailDrawer + ConfirmDialog
 * - ✅ Security: Governance preview + audit_id display
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { CardCollectionWrap } from '@/ui/cards/CardCollectionWrap'
import { ItemCard } from '@/ui/cards/ItemCard'
import type { ItemCardAction } from '@/ui/cards/ItemCard'
import { DetailDrawer } from '@/ui/interaction/DetailDrawer'
import { ConfirmDialog } from '@/ui/interaction/ConfirmDialog'
import {
  FilterBar,
  Box,
  Typography,
  Chip,
  Alert,
  Divider,
  Link,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@/ui'
import { Tooltip } from '@mui/material'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import {
  ExtensionIcon,
  StorageIcon,
  CloudIcon,
  CodeIcon,
  WarningIcon,
  CheckCircleIcon,
} from '@/ui/icons'
import {
  communicationosService,
  type MCPMarketplaceItem,
  type MCPPackageDetail,
  type MCPGovernancePreview,
} from '@services'

// Constants for MUI prop values (to pass ESLint jsx-no-literals)
const SIZE_SMALL = 'small' as const
const VARIANT_H6 = 'h6' as const
const VARIANT_BODY1 = 'body1' as const
const VARIANT_BODY2 = 'body2' as const
const VARIANT_CAPTION = 'caption' as const
const VARIANT_SUBTITLE2 = 'subtitle2' as const
const VARIANT_OUTLINED = 'outlined' as const
const VARIANT_CONTAINED = 'contained' as const
const COLOR_TEXT_SECONDARY = 'text.secondary' as const
const COLOR_ERROR = 'error' as const
const COLOR_SUCCESS = 'success' as const
const COLOR_WARNING = 'warning' as const
const COLOR_DEFAULT = 'default' as const
const SEVERITY_WARNING = 'warning' as const
const LAYOUT_GRID = 'grid' as const
const LINK_TARGET_BLANK = '_blank' as const
const LINK_REL_NOOPENER = 'noopener' as const
const SELECT_VALUE_ALL = 'all' as const

const ICON_MAP: Record<string, JSX.Element> = {
  git: <CodeIcon />,
  github: <CodeIcon />,
  database: <StorageIcon />,
  sql: <StorageIcon />,
  api: <CodeIcon />,
  communication: <CodeIcon />,
  cloud: <CloudIcon />,
  storage: <CloudIcon />,
  default: <ExtensionIcon />,
}

function getIcon(tags: string[]): JSX.Element {
  const lowerTags = tags.map((t) => t.toLowerCase())
  for (const [key, icon] of Object.entries(ICON_MAP)) {
    if (key !== 'default' && lowerTags.some((t) => t.includes(key))) {
      return icon
    }
  }
  return ICON_MAP.default
}

function normalizeMarketplaceItem(raw: any): MCPMarketplaceItem {
  const packageId = String(raw?.package_id || raw?.id || '')
  const tags = Array.isArray(raw?.tags) ? raw.tags.map((t: any) => String(t)) : []
  return {
    package_id: packageId,
    name: String(raw?.name || raw?.display_name || packageId),
    description: raw?.description ? String(raw.description) : '',
    version: String(raw?.version || 'N/A'),
    author: String(raw?.author || 'Unknown'),
    tools_count: typeof raw?.tools_count === 'number' ? raw.tools_count : undefined,
    transport: String(raw?.transport || 'stdio'),
    recommended_trust_tier: String(raw?.recommended_trust_tier || raw?.trust_tier || 'T1'),
    requires_admin_token: Boolean(raw?.requires_admin_token),
    is_connected: Boolean(raw?.is_connected),
    tags,
    downloads: raw?.downloads ? String(raw.downloads) : undefined,
  }
}

type McpServerSummary = {
  server_id: string
  package_id: string
  enabled: boolean
  aws_profile?: string
  aws_region?: string
}

function normalizeServerMap(raw: any): Record<string, McpServerSummary> {
  const servers = Array.isArray(raw?.servers) ? raw.servers : []
  return servers.reduce((acc: Record<string, McpServerSummary>, item: any) => {
    const packageId = String(item?.package_id || item?.env?.OCTOPUSOS_MCP_PACKAGE_ID || '')
    const serverId = String(item?.server_id || item?.id || '')
    if (!packageId || !serverId) return acc
    acc[packageId] = {
      server_id: serverId,
      package_id: packageId,
      enabled: Boolean(item?.enabled),
      aws_profile: item?.aws_profile ? String(item.aws_profile) : undefined,
      aws_region: item?.aws_region ? String(item.aws_region) : undefined,
    }
    return acc
  }, {})
}

function applyServerStatus(
  items: MCPMarketplaceItem[],
  serverMap: Record<string, McpServerSummary>
): MCPMarketplaceItem[] {
  return items.map((item) => ({
    ...item,
    is_connected: Boolean(serverMap[item.package_id]?.enabled),
  }))
}

function mergeMarketplaceItems(
  primary: MCPMarketplaceItem[],
  fallback: MCPMarketplaceItem[]
): MCPMarketplaceItem[] {
  const fallbackByPackage = new Map(fallback.map((item) => [item.package_id, item]))
  return primary.map((item) => {
    const alt = fallbackByPackage.get(item.package_id)
    if (!alt) return item

    const versionMissing = !item.version || item.version === 'N/A'
    const authorMissing = !item.author || item.author === 'Unknown'
    const descMissing = !item.description
    const tagsMissing = !item.tags || item.tags.length === 0

    return {
      ...item,
      version: versionMissing ? alt.version : item.version,
      author: authorMissing ? alt.author : item.author,
      description: descMissing ? alt.description : item.description,
      tags: tagsMissing ? alt.tags : item.tags,
      transport: !item.transport || item.transport === 'stdio' ? alt.transport || item.transport : item.transport,
    }
  })
}

export default function McpMarketplacePage() {
  const { t } = useTextTranslation()
  const getTrustTierTooltip = useCallback((tier: string): string => {
    switch ((tier || '').toUpperCase()) {
      case 'T0':
        return t(K.page.trustTier.descT0)
      case 'T1':
        return t(K.page.trustTier.descT1)
      case 'T2':
        return t(K.page.trustTier.descT2)
      case 'T3':
        return t(K.page.trustTier.descT3)
      default:
        return t(K.page.trustTier.descUnknown)
    }
  }, [t])
  const getTrustTierChipColor = useCallback((tier: string): 'success' | 'warning' | 'default' | 'error' => {
    switch ((tier || '').toUpperCase()) {
      case 'T0':
      case 'T1':
        return COLOR_SUCCESS
      case 'T2':
        return COLOR_WARNING
      case 'T3':
        return COLOR_DEFAULT
      default:
        return COLOR_DEFAULT
    }
  }, [])
  const getRiskDefinition = useCallback((risk: string): string => {
    switch ((risk || '').toUpperCase()) {
      case 'LOW':
        return t(K.page.mcpMarketplace.riskDefinitionLow)
      case 'MEDIUM':
        return t(K.page.mcpMarketplace.riskDefinitionMedium)
      case 'HIGH':
        return t(K.page.mcpMarketplace.riskDefinitionHigh)
      case 'CRITICAL':
        return t(K.page.mcpMarketplace.riskDefinitionCritical)
      default:
        return t(K.page.mcpMarketplace.riskDefinitionUnknown)
    }
  }, [t])
  const mapAdminTokenReason = useCallback((reason: string): string => {
    if (reason === 'side_effects') return t(K.page.mcpMarketplace.adminTokenReasonSideEffects)
    return t(K.page.mcpMarketplace.adminTokenReasonUnknown)
  }, [t])

  // ===================================
  // State Management
  // ===================================
  const [packages, setPackages] = useState<MCPMarketplaceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPackage, setSelectedPackage] = useState<MCPPackageDetail | null>(null)
  const [governance, setGovernance] = useState<MCPGovernancePreview | null>(null)
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false)
  const [installDialogOpen, setInstallDialogOpen] = useState(false)
  const [packageToInstall, setPackageToInstall] = useState<MCPMarketplaceItem | null>(null)
  const [installing, setInstalling] = useState(false)
  const [installProfile, setInstallProfile] = useState('default')
  const [installProfileManual, setInstallProfileManual] = useState(false)
  const [installRegion, setInstallRegion] = useState('')
  const [availableAwsProfiles, setAvailableAwsProfiles] = useState<string[]>([])
  const [awsProfilesLoading, setAwsProfilesLoading] = useState(false)
  const [uninstallDialogOpen, setUninstallDialogOpen] = useState(false)
  const [packageToUninstall, setPackageToUninstall] = useState<MCPMarketplaceItem | null>(null)
  const [uninstalling, setUninstalling] = useState(false)
  const [serverByPackage, setServerByPackage] = useState<Record<string, McpServerSummary>>({})
  const [preflightDrawerOpen, setPreflightDrawerOpen] = useState(false)
  const [preflightPackageId, setPreflightPackageId] = useState<string | null>(null)
  const [preflightReport, setPreflightReport] = useState<any>(null)
  const [preflighting, setPreflighting] = useState(false)
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false)
  const [configPackageId, setConfigPackageId] = useState<string | null>(null)
  const [configServerId, setConfigServerId] = useState<string | null>(null)
  const [configProfile, setConfigProfile] = useState('default')
  const [configProfileManual, setConfigProfileManual] = useState(false)
  const [configRegion, setConfigRegion] = useState('')
  const [configuring, setConfiguring] = useState(false)
  const [configProfilesLoading, setConfigProfilesLoading] = useState(false)
  const [configProfiles, setConfigProfiles] = useState<string[]>([])
  const [enablingPackageId, setEnablingPackageId] = useState<string | null>(null)
  const [disablingPackageId, setDisablingPackageId] = useState<string | null>(null)

  // ===================================
  // P1-13: Search & Filter State
  // ===================================
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [connectedOnly, setConnectedOnly] = useState(false)

  // ===================================
  // P0-11: List API Integration
  // ===================================
  const loadPackages = useCallback(async () => {
    setLoading(true)
    try {
      const serversResponse = await communicationosService.listMcpServersApiMcpServersGet()
      const serverMap = normalizeServerMap(serversResponse)
      setServerByPackage(serverMap)

      // Prefer catalog endpoint and normalize shape to prevent UI from breaking on field drift.
      const catalogResponse = await communicationosService.getMcpCatalogApiMcpMarketplaceCatalogGet()
      const catalogItems = Array.isArray(catalogResponse?.packages) ? catalogResponse.packages : []
      const packagesResponse = await communicationosService.listMcpPackagesApiMcpMarketplacePackagesGet()
      const listedItems = Array.isArray(packagesResponse?.packages) ? packagesResponse.packages : []
      const normalizedListed = listedItems.map(normalizeMarketplaceItem)
      if (catalogItems.length > 0) {
        const normalizedCatalog = catalogItems.map(normalizeMarketplaceItem)
        setPackages(applyServerStatus(mergeMarketplaceItems(normalizedCatalog, normalizedListed), serverMap))
      } else {
        setPackages(applyServerStatus(normalizedListed, serverMap))
      }
    } catch (error) {
      console.error('Failed to load MCP packages:', error)
      toast.error(t(K.page.mcpMarketplace.installError))
      setServerByPackage({})
      setPackages([])
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    loadPackages()
  }, [loadPackages])

  // ===================================
  // P1-13: Filter & Search Logic
  // ===================================
  const filteredPackages = useMemo(() => {
    let result = packages

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (pkg) =>
          pkg.name.toLowerCase().includes(query) ||
          (pkg.description && pkg.description.toLowerCase().includes(query)) ||
          pkg.author.toLowerCase().includes(query) ||
          pkg.tags.some((tag) => tag.toLowerCase().includes(query))
      )
    }

    // Category filter (tag-based)
    if (selectedCategory !== 'all') {
      result = result.filter((pkg) =>
        pkg.tags.some((tag) => tag.toLowerCase() === selectedCategory.toLowerCase())
      )
    }

    // Connected only filter
    if (connectedOnly) {
      result = result.filter((pkg) => pkg.is_connected)
    }

    return result
  }, [packages, searchQuery, selectedCategory, connectedOnly])

  // Extract unique categories from tags
  const categories = useMemo(() => {
    const uniqueTags = new Set<string>()
    packages.forEach((pkg) => {
      pkg.tags.forEach((tag) => uniqueTags.add(tag))
    })
    return Array.from(uniqueTags).sort()
  }, [packages])

  // Clear all filters
  const handleClearFilters = () => {
    setSearchQuery('')
    setSelectedCategory('all')
    setConnectedOnly(false)
  }

  // ===================================
  // P0-12: Package Detail View
  // ===================================
  const handleViewPackage = async (pkg: MCPMarketplaceItem) => {
    try {
      const [detailResponse, governanceResponse] = await Promise.all([
        communicationosService.getMcpPackageApiMcpMarketplacePackagesPackageIdGet(pkg.package_id),
        communicationosService.getMcpPreviewApiMcpMarketplaceGovernancePreviewPackageIdGet(pkg.package_id),
      ])

      if (detailResponse.ok && detailResponse.data) {
        const attached = Boolean(serverByPackage[pkg.package_id]?.server_id)
        setSelectedPackage({
          ...detailResponse.data,
          is_connected: attached,
        })
      }

      if (governanceResponse.ok && governanceResponse.data) {
        setGovernance(governanceResponse.data)
      }

      setDetailDrawerOpen(true)
    } catch (error) {
      console.error('Failed to load package details:', error)
      toast.error(t(K.page.mcpMarketplace.installError))
    }
  }

  const handleCloseDetailDrawer = () => {
    setDetailDrawerOpen(false)
    setSelectedPackage(null)
    setGovernance(null)
  }

  // ===================================
  // P0-14: Installation Flow
  // ===================================
  const handleInstallClick = (pkg: MCPMarketplaceItem) => {
    const isAwsPackage = pkg.package_id === 'aws.mcp'
    setInstallProfile('default')
    setInstallProfileManual(false)
    setInstallRegion('')
    setAvailableAwsProfiles([])
    setAwsProfilesLoading(isAwsPackage)
    setPackageToInstall(pkg)
    setInstallDialogOpen(true)
  }

  const handleConfirmInstall = async () => {
    if (!packageToInstall) return

    setInstalling(true)
    try {
      const response = await communicationosService.attachMcpPackageApiMcpMarketplaceAttachPost({
        package_id: packageToInstall.package_id,
        config: packageToInstall.package_id === 'aws.mcp'
          ? {
              profile: installProfile || 'default',
              region: installRegion.trim() || undefined,
            }
          : {},
      })

      if (response.ok && response.data) {
        const { audit_id, warnings, next_steps } = response.data

        // Build success message with audit_id
        const message = `${t(K.page.mcpMarketplace.installSuccess)}\n${t(K.page.mcpMarketplace.auditId)}: ${audit_id}`
        toast.success(message)

        // Show warnings if any
        if (warnings && warnings.length > 0) {
          toast.warning(`${t(K.page.mcpMarketplace.detailWarnings)}:\n${warnings.join('\n')}`)
        }

        // Show next steps if any
        if (next_steps && next_steps.length > 0) {
          console.info('Next steps:', next_steps)
        }

        // Reload packages to reflect new connection status
        await loadPackages()

        // Close dialogs
        setInstallDialogOpen(false)
        setDetailDrawerOpen(false)
        setPackageToInstall(null)
        setInstallProfile('default')
        setInstallProfileManual(false)
        setInstallRegion('')
        setAvailableAwsProfiles([])
      }
    } catch (error) {
      console.error('Failed to install package:', error)
      toast.error(t(K.page.mcpMarketplace.installError))
    } finally {
      setInstalling(false)
    }
  }

  const handleCancelInstall = () => {
    setInstallDialogOpen(false)
    setPackageToInstall(null)
    setInstallProfile('default')
    setInstallProfileManual(false)
    setInstallRegion('')
    setAvailableAwsProfiles([])
  }

  useEffect(() => {
    if (!installDialogOpen || packageToInstall?.package_id !== 'aws.mcp') return
    let cancelled = false
    const loadAwsProfiles = async () => {
      setAwsProfilesLoading(true)
      try {
        const resp = await communicationosService.listLocalAwsProfiles()
        const profiles = Array.isArray(resp?.profiles) ? resp.profiles : []
        if (cancelled) return
        setAvailableAwsProfiles(profiles)
        setInstallProfileManual(profiles.length === 0)
        if (profiles.length > 0) {
          setInstallProfile(resp.default_profile && profiles.includes(resp.default_profile) ? resp.default_profile : profiles[0])
        }
      } catch (error) {
        if (!cancelled) {
          setAvailableAwsProfiles([])
          setInstallProfileManual(true)
        }
      } finally {
        if (!cancelled) {
          setAwsProfilesLoading(false)
        }
      }
    }
    void loadAwsProfiles()
    return () => {
      cancelled = true
    }
  }, [installDialogOpen, packageToInstall?.package_id])

  // ===================================
  // P2-5: Uninstall Functionality
  // ===================================
  const handleUninstallClick = (pkg: MCPMarketplaceItem) => {
    setPackageToUninstall(pkg)
    setUninstallDialogOpen(true)
  }

  const handleConfirmUninstall = async () => {
    if (!packageToUninstall) return

    setUninstalling(true)
    try {
      const response =
        await communicationosService.uninstallMcpPackageCanonicalApiMcpMarketplacePackagesPackageIdDelete(
          packageToUninstall.package_id
        )

      if (response.ok && response.data) {
        const { audit_id, warnings } = response.data

        // Build success message with audit_id
        const message = `${t(K.page.mcpMarketplace.uninstallSuccess)}\n${t(K.page.mcpMarketplace.auditId)}: ${audit_id}`
        toast.success(message)

        // Show warnings if any
        if (warnings && warnings.length > 0) {
          toast.warning(`${t(K.page.mcpMarketplace.detailWarnings)}:\n${warnings.join('\n')}`)
        }

        // Reload packages to reflect new connection status
        await loadPackages()

        // Close dialogs
        setUninstallDialogOpen(false)
        setDetailDrawerOpen(false)
        setPackageToUninstall(null)
      }
    } catch (error) {
      console.error('Failed to uninstall package:', error)
      toast.error(t(K.page.mcpMarketplace.uninstallError))
    } finally {
      setUninstalling(false)
    }
  }

  const handleCancelUninstall = () => {
    setUninstallDialogOpen(false)
    setPackageToUninstall(null)
  }

  const handlePreflightClick = async (pkg: MCPMarketplaceItem) => {
    const server = serverByPackage[pkg.package_id]
    if (!server) {
      toast.warning(t(K.page.mcpMarketplace.installFirst))
      return
    }
    setPreflighting(true)
    try {
      const report = await communicationosService.preflightMcpServerApiMcpServersServerIdPreflightGet(server.server_id)
      setPreflightPackageId(pkg.package_id)
      setPreflightReport(report)
      setPreflightDrawerOpen(true)
    } catch (error) {
      console.error('Failed to preflight MCP server:', error)
      toast.error(t(K.page.mcpMarketplace.preflightFailed))
    } finally {
      setPreflighting(false)
    }
  }

  const handleEnableClick = async (pkg: MCPMarketplaceItem) => {
    const server = serverByPackage[pkg.package_id]
    if (!server) return
    setEnablingPackageId(pkg.package_id)
    try {
      await communicationosService.enableMcpServerApiMcpServersServerIdEnablePost(server.server_id, {
        auto_install: true,
      })
      toast.success(t(K.page.mcpMarketplace.enableSuccess))
      await loadPackages()
    } catch (error) {
      console.error('Failed to enable MCP server:', error)
      toast.error(t(K.page.mcpMarketplace.enableError))
    } finally {
      setEnablingPackageId(null)
    }
  }

  const handleDisableClick = async (pkg: MCPMarketplaceItem) => {
    const server = serverByPackage[pkg.package_id]
    if (!server) return
    setDisablingPackageId(pkg.package_id)
    try {
      await communicationosService.disableMcpServerApiMcpServersServerIdDisablePost(server.server_id)
      toast.success(t(K.page.mcpMarketplace.disableSuccess))
      await loadPackages()
    } catch (error) {
      console.error('Failed to disable MCP server:', error)
      toast.error(t(K.page.mcpMarketplace.disableError))
    } finally {
      setDisablingPackageId(null)
    }
  }

  const handleOpenConfigDrawer = async (pkg: MCPMarketplaceItem) => {
    const server = serverByPackage[pkg.package_id]
    if (!server) {
      toast.warning(t(K.page.mcpMarketplace.installFirst))
      return
    }
    setConfigPackageId(pkg.package_id)
    setConfigServerId(server.server_id)
    setConfigProfile(server.aws_profile || 'default')
    setConfigRegion(server.aws_region || '')
    setConfigProfileManual(false)
    setConfigDrawerOpen(true)
    setConfigProfilesLoading(true)
    try {
      const resp = await communicationosService.listLocalAwsProfiles()
      const profiles = Array.isArray(resp?.profiles) ? resp.profiles : []
      setConfigProfiles(profiles)
      setConfigProfileManual(profiles.length === 0)
      if (profiles.length > 0 && !profiles.includes(server.aws_profile || '')) {
        setConfigProfile(resp.default_profile && profiles.includes(resp.default_profile) ? resp.default_profile : profiles[0])
      }
    } catch (error) {
      setConfigProfiles([])
      setConfigProfileManual(true)
    } finally {
      setConfigProfilesLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    if (!configServerId) return
    setConfiguring(true)
    try {
      await communicationosService.updateMCPServerConfig(configServerId, {
        profile: configProfile,
        region: configRegion,
      })
      toast.success(t(K.page.mcpMarketplace.configSaveSuccess))
      setConfigDrawerOpen(false)
      await loadPackages()
    } catch (error) {
      console.error('Failed to update MCP server config:', error)
      toast.error(t(K.page.mcpMarketplace.configSaveError))
    } finally {
      setConfiguring(false)
    }
  }

  const handleCloseConfigDrawer = () => {
    setConfigDrawerOpen(false)
    setConfigPackageId(null)
    setConfigServerId(null)
    setConfigProfile('default')
    setConfigProfileManual(false)
    setConfigRegion('')
    setConfigProfiles([])
  }

  const handleClosePreflightDrawer = () => {
    setPreflightDrawerOpen(false)
    setPreflightPackageId(null)
    setPreflightReport(null)
  }

  // ===================================
  // Page Header & Actions
  // ===================================
  usePageHeader({
    title: t(K.page.mcpMarketplace.title),
    subtitle: t(K.page.mcpMarketplace.subtitle),
  })

  usePageActions([
    {
      key: 'refresh',
      label: t('common.refresh'),
      variant: 'outlined',
      onClick: loadPackages,
    },
    {
      key: 'discover',
      label: t(K.page.mcpMarketplace.discoverServers),
      variant: 'contained',
      onClick: loadPackages,
    },
  ])

  return (
    <>
      {/* P1-13: Filter Bar */}
      <FilterBar
        filters={[
          {
            width: 6,
            component: (
              <TextField
                label={t(K.common.search)}
                placeholder={t(K.page.mcpMarketplace.searchPlaceholder)}
                fullWidth
                size={SIZE_SMALL}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            ),
          },
          {
            width: 3,
            component: (
              <Select
                label={t(K.page.mcpMarketplace.filterCategory)}
                fullWidth
                size={SIZE_SMALL}
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <MenuItem value={SELECT_VALUE_ALL}>{t(K.page.mcpMarketplace.categoryAll)}</MenuItem>
                {categories.map((category) => (
                  <MenuItem key={category} value={category}>
                    {category}
                  </MenuItem>
                ))}
              </Select>
            ),
          },
          {
            width: 3,
            component: (
              <Box data-testid="mcp-filter-connected-only">
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={connectedOnly}
                      onChange={(e) => setConnectedOnly(e.target.checked)}
                    />
                  }
                  label={t(K.page.mcpMarketplace.connectedOnly)}
                />
              </Box>
            ),
          },
        ]}
        actions={[
          {
            key: 'clear',
            label: t(K.page.mcpMarketplace.clearFilters),
            onClick: handleClearFilters,
          },
        ]}
      />

      {/* Card Grid */}
      <Box sx={{ mt: 2 }}>
        <CardCollectionWrap layout={LAYOUT_GRID} columns={3} gap={16} loading={loading}>
          {filteredPackages.length === 0 && !loading ? (
            <Box sx={{ gridColumn: '1 / -1', textAlign: 'center', py: 8 }}>
              <Typography
                data-testid="mcp-marketplace-empty-state"
                variant={VARIANT_BODY1}
                color={COLOR_TEXT_SECONDARY}
              >
                {connectedOnly || searchQuery.trim() || selectedCategory !== SELECT_VALUE_ALL
                  ? `${t(K.page.mcpMarketplace.noPackages)} · ${t(K.page.mcpMarketplace.clearFilters)}`
                  : t(K.page.mcpMarketplace.noPackages)}
              </Typography>
            </Box>
          ) : (
            filteredPackages.map((pkg) => (
              (() => {
                const server = serverByPackage[pkg.package_id]
                const attached = Boolean(server?.server_id)
                const enabled = Boolean(server?.enabled)
                const statusLabel = !attached
                  ? t(K.page.mcpMarketplace.statusNotInstalled)
                  : enabled
                    ? t(K.page.mcpMarketplace.statusEnabled)
                    : t(K.page.mcpMarketplace.statusInstalledDisabled)

                const actions: ItemCardAction[] = [
                  {
                    key: 'view',
                    testId: `mcp-marketplace-action-view-${pkg.package_id}`,
                    label: t(K.page.mcpMarketplace.actionView),
                    variant: 'outlined' as const,
                    onClick: () => { void handleViewPackage(pkg) },
                  },
                ]

                if (!attached) {
                  actions.push({
                    key: 'install',
                    testId: `mcp-marketplace-action-install-${pkg.package_id}`,
                    label: t(K.page.mcpMarketplace.actionInstall),
                    variant: 'contained' as const,
                    onClick: () => { handleInstallClick(pkg) },
                  })
                } else {
                  actions.push({
                    key: 'preflight',
                    testId: `mcp-marketplace-action-preflight-${pkg.package_id}`,
                    label: t(K.page.mcpMarketplace.actionPreflight),
                    variant: 'outlined' as const,
                    onClick: () => { void handlePreflightClick(pkg) },
                    disabled: preflighting && preflightPackageId === pkg.package_id,
                  })
                  if (pkg.package_id === 'aws.mcp') {
                    actions.push({
                      key: 'configure',
                      testId: `mcp-marketplace-action-configure-${pkg.package_id}`,
                      label: t(K.page.mcpMarketplace.actionConfigure),
                      variant: 'outlined' as const,
                      onClick: () => { void handleOpenConfigDrawer(pkg) },
                    })
                  }
                  actions.push(
                    enabled
                      ? {
                          key: 'disable',
                          testId: `mcp-marketplace-action-disable-${pkg.package_id}`,
                          label: t(K.page.mcpMarketplace.actionDisable),
                          variant: 'outlined' as const,
                          onClick: () => { void handleDisableClick(pkg) },
                          disabled: disablingPackageId === pkg.package_id,
                        }
                      : {
                          key: 'enable',
                          testId: `mcp-marketplace-action-enable-${pkg.package_id}`,
                          label: t(K.page.mcpMarketplace.actionEnable),
                          variant: 'contained' as const,
                          onClick: () => { void handleEnableClick(pkg) },
                          disabled: enablingPackageId === pkg.package_id,
                        }
                  )
                  actions.push({
                    key: 'uninstall',
                    testId: `mcp-marketplace-action-uninstall-${pkg.package_id}`,
                    label: t(K.page.mcpMarketplace.actionUninstall),
                    variant: 'outlined' as const,
                    onClick: () => { handleUninstallClick(pkg) },
                  })
                }

                return (
                  <ItemCard
                    key={pkg.package_id}
                    testId={`mcp-marketplace-item-${pkg.package_id}`}
                    title={pkg.name}
                    description={pkg.description}
                    meta={[
                      { key: 'version', label: t(K.page.mcpMarketplace.metaVersion), value: pkg.version },
                      { key: 'author', label: t(K.page.mcpMarketplace.metaAuthor), value: pkg.author },
                      {
                        key: 'trust_tier',
                        label: t(K.page.mcpMarketplace.metaTrustTier),
                        value: (
                          <Tooltip title={getTrustTierTooltip(pkg.recommended_trust_tier)}>
                            <Chip
                              label={pkg.recommended_trust_tier}
                              size={SIZE_SMALL}
                              color={getTrustTierChipColor(pkg.recommended_trust_tier)}
                              sx={{ height: 20 }}
                            />
                          </Tooltip>
                        ),
                      },
                    ]}
                    tags={[statusLabel, ...pkg.tags]}
                    footer={
                      <Typography
                        data-testid={`mcp-marketplace-status-${pkg.package_id}`}
                        variant={VARIANT_CAPTION}
                        color={COLOR_TEXT_SECONDARY}
                      >
                        {statusLabel}
                      </Typography>
                    }
                    icon={getIcon(pkg.tags)}
                    actions={actions}
                    onClick={() => handleViewPackage(pkg)}
                  />
                )
              })()
            ))
          )}
        </CardCollectionWrap>
      </Box>

      {/* P0-12: Detail Drawer */}
      <DetailDrawer
        open={detailDrawerOpen}
        onClose={handleCloseDetailDrawer}
        title={selectedPackage?.name || ''}
        subtitle={selectedPackage?.version || ''}
        actions={
          selectedPackage && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              {Boolean(serverByPackage[selectedPackage.package_id]?.server_id) ? (
                <Button
                  variant={VARIANT_OUTLINED}
                  color={COLOR_ERROR}
                  onClick={() => handleUninstallClick({
                    package_id: selectedPackage.package_id,
                    name: selectedPackage.name,
                    version: selectedPackage.version,
                    author: selectedPackage.author,
                    description: selectedPackage.description,
                    transport: selectedPackage.transport,
                    recommended_trust_tier: selectedPackage.recommended_trust_tier,
                    requires_admin_token: selectedPackage.requires_admin_token,
                    is_connected: Boolean(serverByPackage[selectedPackage.package_id]?.server_id),
                    tags: selectedPackage.tags,
                  })}
                >
                  {t(K.page.mcpMarketplace.actionUninstall)}
                </Button>
              ) : (
                <Button
                  variant={VARIANT_CONTAINED}
                  onClick={() => handleInstallClick({
                    package_id: selectedPackage.package_id,
                    name: selectedPackage.name,
                    version: selectedPackage.version,
                    author: selectedPackage.author,
                    description: selectedPackage.description,
                    transport: selectedPackage.transport,
                    recommended_trust_tier: selectedPackage.recommended_trust_tier,
                    requires_admin_token: selectedPackage.requires_admin_token,
                    is_connected: Boolean(serverByPackage[selectedPackage.package_id]?.server_id),
                    tags: selectedPackage.tags,
                  })}
                >
                  {t(K.page.mcpMarketplace.actionInstall)}
                </Button>
              )}
            </Box>
          )
        }
      >
        {selectedPackage && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Status Badge */}
            <Box>
              <Chip
                icon={Boolean(serverByPackage[selectedPackage.package_id]?.server_id) ? <CheckCircleIcon /> : undefined}
                label={
                  Boolean(serverByPackage[selectedPackage.package_id]?.server_id)
                    ? t(K.page.mcpMarketplace.statusConnected)
                    : t(K.page.mcpMarketplace.statusAvailable)
                }
                color={Boolean(serverByPackage[selectedPackage.package_id]?.server_id) ? COLOR_SUCCESS : COLOR_DEFAULT}
                size={SIZE_SMALL}
              />
            </Box>

            {/* Description */}
            <Box>
              <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                {t(K.page.mcpMarketplace.detailDescription)}
              </Typography>
              <Typography variant={VARIANT_BODY2}>{selectedPackage.description}</Typography>
            </Box>

            {/* Long Description */}
            {selectedPackage.long_description && (
              <Box>
                <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                  {t(K.page.mcpMarketplace.detailLongDescription)}
                </Typography>
                <Typography
                  variant={VARIANT_BODY2}
                  sx={{ whiteSpace: 'pre-line' }}
                >
                  {selectedPackage.long_description}
                </Typography>
              </Box>
            )}

            {/* Metadata */}
            <Box>
              <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                {t(K.page.mcpMarketplace.metaAuthor)}
              </Typography>
              <Typography variant={VARIANT_BODY2}>{selectedPackage.author}</Typography>
            </Box>

            <Box>
              <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                {t(K.page.mcpMarketplace.detailTransport)}
              </Typography>
              <Typography variant={VARIANT_BODY2}>{selectedPackage.transport}</Typography>
            </Box>

            {selectedPackage.license && (
              <Box>
                <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                  {t(K.page.mcpMarketplace.detailLicense)}
                </Typography>
                <Typography variant={VARIANT_BODY2}>{selectedPackage.license}</Typography>
              </Box>
            )}

            {/* Links */}
            {(selectedPackage.homepage || selectedPackage.repository) && (
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {selectedPackage.homepage && (
                  <Link href={selectedPackage.homepage} target={LINK_TARGET_BLANK} rel={LINK_REL_NOOPENER}>
                    {t(K.page.mcpMarketplace.detailHomepage)}
                  </Link>
                )}
                {selectedPackage.repository && (
                  <Link href={selectedPackage.repository} target={LINK_TARGET_BLANK} rel={LINK_REL_NOOPENER}>
                    {t(K.page.mcpMarketplace.detailRepository)}
                  </Link>
                )}
              </Box>
            )}

            <Divider />

            {/* P0-13: Governance Preview */}
            {governance && (
              <Box>
                <Typography variant={VARIANT_H6} gutterBottom>
                  {t(K.page.mcpMarketplace.detailGovernance)}
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                  <Box>
                    <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
                      {t(K.page.mcpMarketplace.detailTrustTier)}
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Tooltip title={getTrustTierTooltip(selectedPackage.recommended_trust_tier)}>
                        <Chip
                          label={selectedPackage.recommended_trust_tier}
                          size={SIZE_SMALL}
                          color={getTrustTierChipColor(selectedPackage.recommended_trust_tier)}
                        />
                      </Tooltip>
                    </Box>
                  </Box>

                  <Box>
                    <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
                      {t(K.page.mcpMarketplace.detailRiskLevel)}
                    </Typography>
                    <Tooltip title={getRiskDefinition(governance.inferred_risk_level)}>
                      <Chip
                        label={governance.inferred_risk_level}
                        color={
                          governance.inferred_risk_level === 'HIGH'
                            ? COLOR_ERROR
                            : governance.inferred_risk_level === 'MEDIUM'
                            ? COLOR_WARNING
                            : COLOR_SUCCESS
                        }
                        size={SIZE_SMALL}
                        sx={{ ml: 1 }}
                      />
                    </Tooltip>
                  </Box>

                  <Box>
                    <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                      {t(K.page.mcpMarketplace.detailQuota)}
                    </Typography>
                    <Box sx={{ ml: 2 }}>
                      <Typography variant={VARIANT_BODY2}>
                        {t(K.page.mcpMarketplace.callsPerMinute)}{': '}{governance.default_quota.calls_per_minute}
                      </Typography>
                      <Typography variant={VARIANT_BODY2}>
                        {t(K.page.mcpMarketplace.maxConcurrent)}{': '}{governance.default_quota.max_concurrent}
                      </Typography>
                      <Typography variant={VARIANT_BODY2}>
                        {t(K.page.mcpMarketplace.maxRuntime)}{': '}{governance.default_quota.max_runtime_ms}{'ms'}
                      </Typography>
                    </Box>
                  </Box>

                  {governance.requires_admin_token_for.length > 0 && (
                    <Alert severity={SEVERITY_WARNING} icon={<WarningIcon />}>
                      <Typography variant={VARIANT_BODY2}>
                        {t(K.page.mcpMarketplace.requiresAdminTokenFor)}{': '}
                        {governance.requires_admin_token_for.map((reason: string) => mapAdminTokenReason(reason)).join(', ')}
                      </Typography>
                      {governance.requires_admin_token_for.includes('side_effects') && (
                        <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} sx={{ mt: 0.5 }}>
                          {t(K.page.mcpMarketplace.adminTokenReasonSideEffectsHint)}
                        </Typography>
                      )}
                    </Alert>
                  )}

                  {governance.gate_warnings.length > 0 && (
                    <Box>
                      <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
                        {t(K.page.mcpMarketplace.detailWarnings)}
                      </Typography>
                      {governance.gate_warnings.map((warning, idx) => (
                        <Alert key={idx} severity={SEVERITY_WARNING} sx={{ mt: 1 }}>
                          {warning}
                        </Alert>
                      ))}
                    </Box>
                  )}
                </Box>
              </Box>
            )}

            <Divider />

            {/* Tools */}
            <Box>
              <Typography variant={VARIANT_H6} gutterBottom>
                {t(K.page.mcpMarketplace.detailTools)}{' ('}{selectedPackage.tools.length}{')'}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                {selectedPackage.tools.map((tool, idx) => (
                  <Box key={idx} sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                    <Typography variant={VARIANT_SUBTITLE2} gutterBottom>
                      {tool.name}
                    </Typography>
                    <Typography variant={VARIANT_BODY2} color={COLOR_TEXT_SECONDARY}>
                      {tool.description}
                    </Typography>
                    {tool.requires_confirmation && (
                      <Chip
                        label={t(K.page.mcpMarketplace.requiresConfirmation)}
                        size={SIZE_SMALL}
                        color={COLOR_WARNING}
                        sx={{ mt: 1 }}
                      />
                    )}
                  </Box>
                ))}
              </Box>
            </Box>

            {/* Tags */}
            <Box>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {selectedPackage.tags.map((tag) => (
                  <Chip key={tag} label={tag} size={SIZE_SMALL} variant={VARIANT_OUTLINED} />
                ))}
              </Box>
            </Box>
          </Box>
        )}
      </DetailDrawer>

      <DetailDrawer
        open={preflightDrawerOpen}
        onClose={handleClosePreflightDrawer}
        title={t(K.page.mcpMarketplace.preflightTitle)}
        subtitle={preflightPackageId || ''}
        actions={(
          <Button data-testid="mcp-preflight-close" onClick={handleClosePreflightDrawer}>
            {t(K.common.close)}
          </Button>
        )}
      >
        <Box data-testid="mcp-preflight-report" sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography data-testid="mcp-preflight-ok" variant={VARIANT_BODY2}>
            {t(K.page.mcpMarketplace.preflightOk)}: {String(Boolean(preflightReport?.ok))}
          </Typography>

          <Box>
            <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
              {t(K.page.mcpMarketplace.preflightChecks)}
            </Typography>
            {(Array.isArray(preflightReport?.checks) ? preflightReport.checks : []).map((check: any, idx: number) => (
              <Typography key={idx} variant={VARIANT_BODY2} data-testid={`mcp-preflight-check-${idx}`}>
                {check?.name}: {String(Boolean(check?.ok))} {check?.details ? `- ${check.details}` : ''}
              </Typography>
            ))}
          </Box>

          <Box>
            <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY} gutterBottom>
              {t(K.page.mcpMarketplace.preflightPlannedActions)}
            </Typography>
            {(Array.isArray(preflightReport?.planned_actions) ? preflightReport.planned_actions : []).map((action: any, idx: number) => (
              <Typography key={idx} variant={VARIANT_BODY2} data-testid={`mcp-preflight-action-${idx}`}>
                {action?.type || 'action'} {action?.tool ? `(${action.tool})` : ''} {action?.details ? `- ${action.details}` : ''}
              </Typography>
            ))}
          </Box>

          {(Array.isArray(preflightReport?.warnings) ? preflightReport.warnings : []).map((warning: string, idx: number) => (
            <Alert key={idx} severity={SEVERITY_WARNING}>
              {warning}
            </Alert>
          ))}
        </Box>
      </DetailDrawer>

      <DetailDrawer
        open={configDrawerOpen}
        onClose={handleCloseConfigDrawer}
        title={t(K.page.mcpMarketplace.configTitle)}
        subtitle={configPackageId || ''}
        actions={(
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button onClick={handleCloseConfigDrawer} disabled={configuring}>
              {t(K.common.cancel)}
            </Button>
            <Button
              data-testid="mcp-config-save"
              variant={VARIANT_CONTAINED}
              onClick={() => { void handleSaveConfig() }}
              disabled={configuring || !configProfile}
            >
              {t(K.page.mcpMarketplace.configSave)}
            </Button>
          </Box>
        )}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
            {t(K.page.mcpMarketplace.installDialogProfileLabel)}
          </Typography>
          {!configProfileManual ? (
            <Select
              value={configProfile}
              onChange={(e) => setConfigProfile(String(e.target.value || 'default'))}
              fullWidth
              size={SIZE_SMALL}
              inputProps={{ 'data-testid': 'mcp-config-aws-profile' }}
            >
              {configProfiles.length > 0
                ? configProfiles.map((profile) => (
                    <MenuItem key={profile} value={profile}>{profile}</MenuItem>
                  ))
                : (
                    <MenuItem value={configProfile || 'default'}>{configProfile || 'default'}</MenuItem>
                  )}
            </Select>
          ) : (
            <TextField
              value={configProfile}
              onChange={(e) => setConfigProfile(e.target.value)}
              fullWidth
              size={SIZE_SMALL}
              placeholder={t(K.page.mcpMarketplace.installDialogProfileManualPlaceholder)}
              inputProps={{ 'data-testid': 'mcp-config-aws-profile-manual' }}
            />
          )}
          <FormControlLabel
            control={
              <Checkbox
                checked={configProfileManual}
                onChange={(e) => setConfigProfileManual(e.target.checked)}
              />
            }
            label={t(K.page.mcpMarketplace.installDialogProfileManualToggle)}
          />
          <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
            {configProfilesLoading
              ? t(K.page.mcpMarketplace.installDialogProfileLoading)
              : t(K.page.mcpMarketplace.installDialogProfileHelp)}
          </Typography>
          <TextField
            label={t(K.page.mcpMarketplace.installDialogRegionLabel)}
            placeholder={t(K.page.mcpMarketplace.installDialogRegionPlaceholder)}
            value={configRegion}
            onChange={(e) => setConfigRegion(e.target.value)}
            size={SIZE_SMALL}
            fullWidth
            inputProps={{ 'data-testid': 'mcp-config-aws-region' }}
          />
        </Box>
      </DetailDrawer>

      {/* P0-14: Install Confirmation Dialog */}
      {packageToInstall && (
        <Dialog open={installDialogOpen} onClose={installing ? undefined : handleCancelInstall} maxWidth="sm" fullWidth>
          <DialogTitle>{t(K.page.mcpMarketplace.installDialogTitle)}</DialogTitle>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant={VARIANT_BODY2} color={COLOR_TEXT_SECONDARY}>
              {t(K.page.mcpMarketplace.installDialogMessage)}
            </Typography>
            <Typography variant={VARIANT_BODY2}>
              {t(K.page.mcpMarketplace.installDialogPackageLabel)}{': '}{packageToInstall.name}
            </Typography>
            <Typography variant={VARIANT_BODY2}>
              {t(K.page.mcpMarketplace.installDialogVersionLabel)}{': '}{packageToInstall.version}
            </Typography>
            <Typography variant={VARIANT_BODY2}>
              {t(K.page.mcpMarketplace.installDialogTrustTierLabel)}{': '}{packageToInstall.recommended_trust_tier}
            </Typography>

            {packageToInstall.package_id === 'aws.mcp' && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
                  {t(K.page.mcpMarketplace.installDialogProfileLabel)}
                </Typography>
                {!installProfileManual ? (
                  <Select
                    value={installProfile}
                    onChange={(e) => setInstallProfile(String(e.target.value || 'default'))}
                    displayEmpty
                    fullWidth
                    size={SIZE_SMALL}
                    inputProps={{ 'data-testid': 'mcp-install-aws-profile' }}
                  >
                    {availableAwsProfiles.length > 0
                      ? availableAwsProfiles.map((profile) => (
                          <MenuItem key={profile} value={profile}>{profile}</MenuItem>
                        ))
                      : (
                          <MenuItem value="default">default</MenuItem>
                        )}
                  </Select>
                ) : (
                  <TextField
                    value={installProfile}
                    onChange={(e) => setInstallProfile(e.target.value)}
                    size={SIZE_SMALL}
                    fullWidth
                    placeholder={t(K.page.mcpMarketplace.installDialogProfileManualPlaceholder)}
                    inputProps={{ 'data-testid': 'mcp-install-aws-profile-manual' }}
                  />
                )}
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={installProfileManual}
                      onChange={(e) => setInstallProfileManual(e.target.checked)}
                    />
                  }
                  label={t(K.page.mcpMarketplace.installDialogProfileManualToggle)}
                />
                <Typography variant={VARIANT_CAPTION} color={COLOR_TEXT_SECONDARY}>
                  {awsProfilesLoading
                    ? t(K.page.mcpMarketplace.installDialogProfileLoading)
                    : t(K.page.mcpMarketplace.installDialogProfileHelp)}
                </Typography>
                <TextField
                  label={t(K.page.mcpMarketplace.installDialogRegionLabel)}
                  placeholder={t(K.page.mcpMarketplace.installDialogRegionPlaceholder)}
                  value={installRegion}
                  onChange={(e) => setInstallRegion(e.target.value)}
                  size={SIZE_SMALL}
                  fullWidth
                  inputProps={{ 'data-testid': 'mcp-install-aws-region' }}
                />
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button data-testid="mcp-install-cancel" onClick={handleCancelInstall} disabled={installing}>
              {t(K.common.cancel)}
            </Button>
            <Button
              data-testid="mcp-install-confirm"
              variant={VARIANT_CONTAINED}
              onClick={() => { void handleConfirmInstall() }}
              disabled={installing || (packageToInstall.package_id === 'aws.mcp' && !installProfile)}
            >
              {t(K.page.mcpMarketplace.installDialogConfirm)}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* P2-5: Uninstall Confirmation Dialog */}
      {packageToUninstall && (
        <ConfirmDialog
          open={uninstallDialogOpen}
          onClose={handleCancelUninstall}
          title={t(K.page.mcpMarketplace.uninstallDialogTitle)}
          message={[
            t(K.page.mcpMarketplace.uninstallDialogMessage),
            '',
            `${t(K.page.mcpMarketplace.uninstallDialogPackageLabel)}: ${packageToUninstall.name}`,
          ].join('\n')}
          confirmText={t(K.page.mcpMarketplace.uninstallDialogConfirm)}
          cancelText={t('common.cancel')}
          onConfirm={handleConfirmUninstall}
          cancelButtonTestId="mcp-uninstall-cancel"
          confirmButtonTestId="mcp-uninstall-confirm"
          loading={uninstalling}
          color={COLOR_ERROR}
        />
      )}
    </>
  )
}
