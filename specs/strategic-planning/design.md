# PDF词汇提取器战略规划：技术设计文档

## 架构演进策略

### 当前架构分析
现有架构采用**分层设计模式**，具有良好的模块化基础：
- **接口层**: 定义清晰的抽象接口
- **实现层**: 遵循依赖倒置原则
- **配置层**: 集中配置管理
- **测试层**: 完善的单元测试

### 演进路线图

#### Phase 1: 性能优化层 (立即实施)
```
┌─────────────────────────────────────────┐
│            应用层                        │
├─────────────────────────────────────────┤
│         异步处理引擎                     │
├─────────────────────────────────────────┤
│ 缓存层(LRU+Redis)  │  批量处理器          │
├─────────────────────────────────────────┤
│      现有核心模块(复用)                  │
└─────────────────────────────────────────┘
```

#### Phase 2: 扩展性架构 (中期实施)
```
┌─────────────────────────────────────────┐
│        插件化微内核                      │
├─────────────────────────────────────────┤
│  插件管理器  │  事件总线  │  服务发现       │
├─────────────────────────────────────────┤
│    多词典适配器    │    输出格式引擎       │
├─────────────────────────────────────────┤
│         核心业务能力                      │
└─────────────────────────────────────────┘
```

#### Phase 3: 云原生架构 (长期实施)
```
┌─────────────────────────────────────────┐
│         API网关 + 负载均衡                │
├─────────────────────────────────────────┤
│   微服务集群    │   消息队列    │  缓存层  │
├─────────────────────────────────────────┤
│   对象存储    │   数据库集群   │  搜索层  │
├─────────────────────────────────────────┤
│         容器化基础设施                    │
└─────────────────────────────────────────┘
```

## 详细技术设计

### 1. 异步处理框架设计

#### 1.1 异步任务队列架构
```python
# 任务定义
@dataclass
class ProcessingTask:
    task_id: str
    file_path: str
    config: Dict[str, Any]
    priority: int = 0
    created_at: datetime = None
    
# 任务状态机
class TaskState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 异步处理器
class AsyncProcessor:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    async def submit_task(self, task: ProcessingTask) -> str:
        """提交异步任务"""
        task_id = str(uuid.uuid4())
        await self.task_queue.put((task_id, task))
        return task_id
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """获取任务状态"""
        return self.task_store.get_status(task_id)
```

#### 1.2 进度事件系统
```python
# 事件定义
@dataclass
class ProgressEvent:
    task_id: str
    stage: str
    progress: float
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]

# 事件总线
class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: str, callback: Callable):
        self.subscribers[event_type].append(callback)
    
    async def publish(self, event: ProgressEvent):
        for callback in self.subscribers[event.stage]:
            await callback(event)

# WebSocket实时推送
class WebSocketProgressTracker(ProgressTrackerInterface):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def update_progress(self, stage: str, progress: float, message: str):
        event = ProgressEvent(
            task_id=self.current_task,
            stage=stage,
            progress=progress,
            message=message,
            timestamp=datetime.now()
        )
        await self.event_bus.publish(event)
```

### 2. 缓存系统设计

#### 2.1 多层缓存架构
```python
# 缓存接口
class CacheInterface(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None):
        pass
    
    @abstractmethod
    async def invalidate(self, key: str):
        pass

# 本地LRU缓存
class LocalLRUCache(CacheInterface):
    def __init__(self, max_size: int = 10000):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

# Redis分布式缓存
class RedisCache(CacheInterface):
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

# 缓存管理器
class CacheManager:
    def __init__(self):
        self.caches: List[CacheInterface] = [
            LocalLRUCache(),
            RedisCache(settings.redis_url)
        ]
    
    async def get(self, key: str) -> Optional[Any]:
        for cache in self.caches:
            value = await cache.get(key)
            if value is not None:
                return value
        return None
```

#### 2.2 智能缓存策略
```python
# 词汇缓存键生成
class CacheKeyBuilder:
    @staticmethod
    def for_word(word: str, service: str) -> str:
        return f"vocab:{service}:{hashlib.md5(word.encode()).hexdigest()}"
    
    @staticmethod
    def for_batch(words: List[str], service: str) -> str:
        words_hash = hashlib.md5(
            "".join(sorted(words)).encode()
        ).hexdigest()
        return f"vocab:batch:{service}:{words_hash}"

# 缓存预热策略
class CacheWarmer:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.dictionary_service = DictionaryService()
    
    async def warm_common_words(self):
        """预热常用词汇"""
        common_words = load_word_frequency_list()
        batch_size = 100
        
        for i in range(0, len(common_words), batch_size):
            batch = common_words[i:i+batch_size]
            await self.dictionary_service.batch_lookup(batch)
```

### 3. 插件系统设计

#### 3.1 插件架构
```python
# 插件接口
class PluginInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        pass
    
    @abstractmethod
    def activate(self):
        pass
    
    @abstractmethod
    def deactivate(self):
        pass

# 插件类型定义
class PluginType(Enum):
    DICTIONARY = "dictionary"
    OUTPUT_FORMAT = "output_format"
    PROCESSOR = "processor"
    NOTIFIER = "notifier"

# 插件管理器
class PluginManager:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, List[Callable]] = defaultdict(list)
    
    def load_plugins(self):
        """动态加载插件"""
        for plugin_file in self.plugin_dir.glob("*.py"):
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'Plugin'):
                plugin = module.Plugin()
                self.register_plugin(plugin)
    
    def register_hook(self, hook_name: str, callback: Callable):
        self.hooks[hook_name].append(callback)
    
    async def execute_hooks(self, hook_name: str, *args, **kwargs):
        for callback in self.hooks[hook_name]:
            await callback(*args, **kwargs)
```

#### 3.2 词典插件示例
```python
# 多词典适配器
class MultiDictionaryAdapter(DictionaryServiceInterface):
    def __init__(self):
        self.providers: List[DictionaryServiceInterface] = []
        self.fallback_chain = []
    
    def register_provider(self, provider: DictionaryServiceInterface, priority: int = 0):
        self.providers.append((priority, provider))
        self.providers.sort(key=lambda x: x[0], reverse=True)
    
    async def batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        results = {}
        remaining_words = words.copy()
        
        for priority, provider in self.providers:
            if not remaining_words:
                break
                
            batch_results = await provider.batch_lookup(remaining_words)
            for word, info in batch_results.items():
                if info.has_complete_info:
                    results[word] = info
                    remaining_words.remove(word)
        
        return results

# 具体词典实现
class CambridgeDictionary(DictionaryServiceInterface):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dictionary.cambridge.org/api/v1"
    
    async def get_definition(self, word: str) -> str:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/entries/en/{word}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                return self.extract_chinese_definition(data)
```

### 4. 智能化功能设计

#### 4.1 词汇难度分级系统
```python
# 难度评估器
class VocabularyDifficultyAnalyzer:
    def __init__(self):
        self.frequency_data = load_word_frequency_data()
        self.cefr_mapping = load_cefr_mapping()
    
    def analyze_difficulty(self, word: str) -> DifficultyLevel:
        """分析词汇难度"""
        # 基于频率的难度评估
        frequency = self.frequency_data.get(word.lower(), 0)
        
        if frequency > 10000:
            return DifficultyLevel.A1
        elif frequency > 5000:
            return DifficultyLevel.A2
        elif frequency > 2000:
            return DifficultyLevel.B1
        elif frequency > 500:
            return DifficultyLevel.B2
        elif frequency > 100:
            return DifficultyLevel.C1
        else:
            return DifficultyLevel.C2
    
    def get_cefr_level(self, word: str) -> Optional[str]:
        """获取CEFR等级"""
        return self.cefr_mapping.get(word.lower())

# 学习建议引擎
class LearningRecommendationEngine:
    def __init__(self, user_model: UserModel):
        self.user_model = user_model
        self.memory_model = SpacedRepetitionModel()
    
    def generate_learning_path(self, vocabulary: List[WordInfo]) -> LearningPath:
        """生成个性化学习路径"""
        # 按难度和关联性排序
        difficulty_groups = self.group_by_difficulty(vocabulary)
        
        # 考虑用户已知词汇
        unknown_words = [
            word for word in vocabulary 
            if word.word not in self.user_model.known_words
        ]
        
        # 基于词根词缀分组
        word_families = self.group_word_families(unknown_words)
        
        return LearningPath(
            stages=self.create_learning_stages(word_families),
            estimated_time=self.estimate_learning_time(unknown_words),
            review_schedule=self.memory_model.calculate_schedule(unknown_words)
        )
```

#### 4.2 语义分析引擎
```python
# 词向量模型
class SemanticAnalyzer:
    def __init__(self):
        self.word_vectors = load_word2vec_model()
        self.thesaurus = load_thesaurus()
    
    def find_synonyms(self, word: str, threshold: float = 0.8) -> List[str]:
        """查找同义词"""
        if word not in self.word_vectors:
            return []
        
        similar_words = self.word_vectors.most_similar(word, topn=20)
        return [
            w for w, score in similar_words 
            if score > threshold and w != word
        ]
    
    def group_semantic_clusters(self, words: List[str]) -> List[WordCluster]:
        """语义聚类"""
        vectors = [
            self.word_vectors[word] for word in words 
            if word in self.word_vectors
        ]
        
        if len(vectors) < 2:
            return []
        
        # 使用K-means聚类
        kmeans = KMeans(n_clusters=min(5, len(vectors)))
        labels = kmeans.fit_predict(vectors)
        
        clusters = defaultdict(list)
        for word, label in zip(words, labels):
            clusters[label].append(word)
        
        return [
            WordCluster(
                words=cluster_words,
                centroid=self.calculate_centroid(cluster_words),
                representative=self.find_representative(cluster_words)
            )
            for cluster_words in clusters.values()
        ]
```

### 5. 云原生架构设计

#### 5.1 微服务拆分
```python
# 服务拆分策略
class ServiceRegistry:
    def __init__(self):
        self.services = {
            'pdf-processor': PDFProcessorService(),
            'vocabulary-extractor': VocabularyExtractorService(),
            'dictionary-service': DictionaryService(),
            'pdf-generator': PDFGeneratorService(),
            'notification-service': NotificationService()
        }
    
    async def process_pdf(self, request: ProcessingRequest) -> ProcessingResponse:
        """分布式处理流程"""
        # 1. 上传文件到对象存储
        file_url = await self.services['storage'].upload(request.file)
        
        # 2. 提交处理任务
        task_id = await self.services['pdf-processor'].submit_task(file_url)
        
        # 3. 异步处理链
        workflow = [
            self.services['pdf-processor'],
            self.services['vocabulary-extractor'],
            self.services['dictionary-service'],
            self.services['pdf-generator']
        ]
        
        # 4. 通过消息队列协调
        result = await self.execute_workflow(workflow, task_id)
        
        return ProcessingResponse(
            task_id=task_id,
            status=result.status,
            download_url=result.download_url
        )
```

#### 5.2 容器化部署
```yaml
# docker-compose.yml
version: '3.8'
services:
  api-gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - app
      - redis
      - postgres

  app:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@postgres:5432/vocab
    depends_on:
      - redis
      - postgres

  worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=vocab
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 数据架构设计

### 1. 数据库模型
```python
# SQLAlchemy模型
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_size = Column(Integer)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    result_data = Column(JSON)
    error_message = Column(Text)

class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"
    
    id = Column(Integer, primary_key=True)
    word = Column(String, index=True, unique=True)
    definition = Column(Text)
    pronunciation = Column(String)
    difficulty_level = Column(String(10))
    frequency_rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    word_id = Column(Integer, ForeignKey('vocabulary_entries.id'))
    familiarity_level = Column(Integer, default=0)
    last_reviewed = Column(DateTime)
    next_review = Column(DateTime)
    review_count = Column(Integer, default=0)
```

### 2. 缓存策略
```python
# 缓存键设计
CACHE_PATTERNS = {
    'word_definition': 'vocab:def:{word}:{service}',
    'word_pronunciation': 'vocab:pron:{word}:{service}',
    'batch_lookup': 'vocab:batch:{hash}:{service}',
    'processing_result': 'vocab:result:{job_id}',
    'user_progress': 'vocab:user:{user_id}:progress'
}

# 缓存失效策略
class CacheInvalidator:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def invalidate_word(self, word: str):
        """失效单词相关缓存"""
        patterns = [
            f"vocab:def:{word}:*",
            f"vocab:pron:{word}:*"
        ]
        
        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
```

## 监控和可观测性

### 1. 指标收集
```python
# Prometheus指标
from prometheus_client import Counter, Histogram, Gauge

# 业务指标
PROCESSING_REQUESTS = Counter('vocab_processing_requests_total', 'Total processing requests')
PROCESSING_DURATION = Histogram('vocab_processing_duration_seconds', 'Processing duration')
CACHE_HITS = Counter('vocab_cache_hits_total', 'Cache hits', ['cache_type'])
CACHE_MISSES = Counter('vocab_cache_misses_total', 'Cache misses', ['cache_type'])

# 系统指标
ACTIVE_TASKS = Gauge('vocab_active_tasks', 'Number of active processing tasks')
QUEUE_DEPTH = Gauge('vocab_queue_depth', 'Current queue depth')
MEMORY_USAGE = Gauge('vocab_memory_usage_bytes', 'Memory usage')
```

### 2. 分布式追踪
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class TracedPDFProcessor(PDFProcessorInterface):
    async def extract_text(self, file_path: str) -> str:
        with tracer.start_as_current_span("pdf.extract_text") as span:
            span.set_attribute("file.path", file_path)
            span.set_attribute("file.size", Path(file_path).stat().st_size)
            
            text = await super().extract_text(file_path)
            
            span.set_attribute("text.length", len(text))
            return text
```

## 安全设计

### 1. 认证授权
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        return await get_user(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 2. 文件安全
```python
class SecureFileValidator:
    ALLOWED_EXTENSIONS = {'.pdf'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def validate_file(self, file_path: str) -> bool:
        # 检查文件扩展名
        if not file_path.lower().endswith(tuple(self.ALLOWED_EXTENSIONS)):
            return False
        
        # 检查文件大小
        file_size = Path(file_path).stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return False
        
        # 检查文件头
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'%PDF')
```

## 部署策略

### 1. 蓝绿部署
```yaml
# Kubernetes部署配置
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vocab-app-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vocab-app
      version: blue
  template:
    metadata:
      labels:
        app: vocab-app
        version: blue
    spec:
      containers:
      - name: vocab-app
        image: vocab-app:latest
        ports:
        - containerPort: 8000
```

### 2. 滚动更新
```bash
# 部署脚本
#!/bin/bash
kubectl apply -f k8s/vocab-app-green.yaml
kubectl wait --for=condition=ready pod -l version=green --timeout=300s
kubectl patch service vocab-app -p '{"spec":{"selector":{"version":"green"}}}'
kubectl delete deployment vocab-app-blue
```

## 技术选型对比

| 技术栈 | 选项A | 选项B | 选项C | 推荐 |
|--------|--------|--------|--------|------|
| **异步框架** | asyncio + aiohttp | Trio | Curio | asyncio |
| **缓存** | Redis | Memcached | In-memory | Redis |
| **数据库** | PostgreSQL | MySQL | MongoDB | PostgreSQL |
| **消息队列** | Redis Streams | RabbitMQ | Apache Kafka | Redis |
| **容器编排** | Kubernetes | Docker Swarm | Nomad | Kubernetes |
| **监控** | Prometheus | DataDog | New Relic | Prometheus |
| **日志** | ELK Stack | Fluentd | Splunk | ELK Stack |

## 性能基准测试

### 1. 测试场景
- **单文件处理**: 10MB PDF, 5000词汇
- **批量处理**: 100个文件并发
- **缓存性能**: 10000词汇查询
- **API响应**: 1000并发用户

### 2. 目标指标
- **单文件处理时间**: <30秒
- **并发处理能力**: 10个文件同时处理
- **缓存命中率**: >90%
- **API响应时间**: <500ms (p95)
- **内存使用**: <500MB per worker
- **CPU使用**: <80% per core