# ForManage 机器人 API 接口文档

> 基础路径：`/api`
> 数据格式：JSON
> 鉴权方式：device_id + update_key（见各接口说明）

---

## 1. 机器人注册

机器人首次上线时调用，注册硬件指纹，获取 `device_id` 和 `update_key`。

- **URL**: `POST /api/register`
- **鉴权**: 无

### 请求体 (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hardware_fingerprint | string | 是 | 硬件指纹 SHA256 |
| model | string | 是 | 设备型号：`x86` / `arm` / `voice_module` |
| dept_id | int | 否 | 绑定部门 ID |
| registered_by | string | 否 | 注册负责人 |
| location | string | 否 | 设备部署地点 |

### 请求示例

```json
{
  "hardware_fingerprint": "a1b2c3d4e5f6...",
  "model": "x86",
  "dept_id": 1,
  "registered_by": "张三",
  "location": "3楼会议室"
}
```

### 成功响应 (201)

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | string | 设备 UUID，后续接口使用 |
| update_key | string | 更新密钥，后续接口鉴权用 |

```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "update_key": "demo-update-key"
}
```

### 错误响应

| 状态码 | 场景 | 响应体 |
|--------|------|--------|
| 400 | 请求体不是 JSON | `{"error": "请求体必须是 JSON"}` |
| 400 | 缺少 hardware_fingerprint | `{"error": "缺少 hardware_fingerprint"}` |
| 400 | 缺少 model | `{"error": "缺少 model"}` |
| 400 | model 值非法 | `{"error": "model 必须是 ['x86', 'arm', 'voice_module'] 之一"}` |
| 409 | 硬件指纹已注册 | `{"error": "硬件指纹已存在: ..."}` |

---

## 2. 机器人认证

机器人使用 `device_id` + `update_key` 进行身份认证，获取百炼 API Key。

- **URL**: `POST /api/authenticate`
- **鉴权**: update_key

### 请求体 (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | 是 | 设备 UUID（注册时返回） |
| update_key | string | 是 | 更新密钥（注册时返回） |

### 请求示例

```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "update_key": "b3f1a2c4d5e6f7..."
}
```

### 成功响应 (200)

| 字段 | 类型 | 说明 |
|------|------|------|
| api_key | string | 百炼 API Key（管理员未设置时为空字符串） |
| key_version | int | API Key 版本号，每次重置 +1 |

```json
{
  "api_key": "demo-api-key",
  "key_version": 3
}
```

### 错误响应

| 状态码 | 场景 | 响应体 | 备注 |
|--------|------|--------|------|
| 400 | 请求体不是 JSON | `{"error": "请求体必须是 JSON"}` | |
| 400 | 缺少 device_id | `{"error": "缺少 device_id"}` | |
| 400 | 缺少 update_key | `{"error": "缺少 update_key"}` | |
| 404 | 设备不存在 | `{"error": "设备不存在"}` | device_id 无匹配记录 |
| 403 | 设备已禁用 | `{"error": "设备已禁用"}` | 管理员已禁用该设备 |
| 401 | update_key 错误 | `{"error": "update_key 错误"}` | 同时累加认证失败次数 |

---

## 3. 检查更新

机器人检查是否有文档更新。仅在批次设定的更新时间窗口内（默认 ±1 小时）返回文档列表。

- **URL**: `GET /api/check-update`
- **鉴权**: query 参数传递 device_id + update_key

### 请求参数 (Query String)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | 是 | 设备 UUID |
| update_key | string | 是 | 更新密钥 |

### 请求示例

```
GET /api/check-update?device_id=550e8400-e29b-41d4-a716-446655440000&update_key=b3f1a2c4d5e6f7...
```

### 成功响应 — 无需更新 (200)

未到批次更新时间窗口，或无批次配置。

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | `"wait"` |
| message | string | 提示信息 |

```json
{
  "status": "wait",
  "message": "未到更新时间，批次更新时间为 02:00:00"
}
```

`status: "wait"` 的 message 可能值：

| message | 原因 |
|---------|------|
| `未分配批次，无法更新` | 机器人未绑定批次 |
| `批次不存在` | 批次已被删除 |
| `批次时间配置错误` | 批次 update_time 格式异常 |
| `未到更新时间，批次更新时间为 HH:MM:SS` | 当前不在时间窗口内 |

### 成功响应 — 有更新 (200)

在更新时间窗口内，返回文档下载链接。

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | `"update"` |
| message | string | 提示信息 |
| public_docs | array | 公共文档列表 |
| public_docs[].filename | string | 文件名（不含扩展名） |
| public_docs[].type | string | 文档类型，固定 `"public"` |
| public_docs[].url | string | OSS 临时下载链接 |
| dept_docs | array | 部门文档列表 |
| dept_docs[].filename | string | 文件名（不含扩展名） |
| dept_docs[].type | string | 文档类型，固定 `"dept"` |
| dept_docs[].url | string | OSS 临时下载链接 |

```json
{
  "status": "update",
  "message": "发现 3 个文档更新",
  "public_docs": [
    {
      "filename": "产品手册",
      "type": "public",
      "url": "https://oss-cn-beijing.aliyuncs.com/.../产品手册.md?Expires=..."
    }
  ],
  "dept_docs": [
    {
      "filename": "部门规范A",
      "type": "dept",
      "url": "https://oss-cn-beijing.aliyuncs.com/.../部门规范A.md?Expires=..."
    },
    {
      "filename": "部门规范B",
      "type": "dept",
      "url": "https://oss-cn-beijing.aliyuncs.com/.../部门规范B.md?Expires=..."
    }
  ]
}
```

### 错误响应

| 状态码 | 场景 | 响应体 | 备注 |
|--------|------|--------|------|
| 400 | 缺少参数 | `{"error": "缺少 device_id 或 update_key"}` | |
| 404 | 设备不存在 | `{"error": "设备不存在"}` | |
| 403 | 设备已禁用 | `{"error": "设备已禁用"}` | |
| 401 | update_key 错误 | `{"error": "update_key 错误"}` | 同时累加认证失败次数 |

---

## 附录

### 通用错误格式

所有错误响应统一使用以下格式：

```json
{
  "error": "错误描述信息"
}
```

### 认证机制说明

- 注册时获得 `device_id` 和 `update_key`
- 认证和检查更新接口均需携带这两个参数
- `update_key` 验证使用 HMAC 时序安全比较（`hmac.compare_digest`）
- 认证失败会累加 `auth_failures` 计数，认证成功会重置为 0
- 管理员可在后台重置 `update_key`

### 相关配置项

| 配置 | 默认值 | 说明 |
|------|--------|------|
| UPDATE_WINDOW_TOLERANCE_HOURS | 1 | 更新时间窗口容差（小时） |
| ONLINE_THRESHOLD_MINUTES | 5 | 在线状态判定阈值（分钟） |
| API_KEY_ROTATE_DAYS | 30 | API Key 建议轮换周期（天） |
