import { useState } from 'react'
import { Layout, Input, Button, Card, Table, Form, InputNumber, Select, message, Empty, Image, Typography, Statistic, Row, Col, Progress } from 'antd'
import { CloudDownloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import axios from 'axios'
import './App.css'

const { Header, Content } = Layout
const { Option } = Select
const { Paragraph, Title } = Typography

function App() {
  const [loading, setLoading] = useState(false)
  const [crawlResults, setCrawlResults] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [form] = Form.useForm()

  // 处理图片URL，添加代理
  const processImageUrl = (url: string) => {
    // 如果是B站图片
    if (url.includes('hdslb.com')) {
      return `http://localhost:5000/proxy_image?url=${encodeURIComponent(url)}&referer=https://www.bilibili.com`
    }
    // 如果是豆瓣图片
    if (url.includes('doubanio.com') || url.includes('douban.com')) {
      return `http://localhost:5000/proxy_image?url=${encodeURIComponent(url)}&referer=https://book.douban.com`
    }
    return url
  }

  const renderPerformanceMetrics = (metrics: any) => {
    if (!metrics) return null;
    
    return (
      <div className="performance-metrics">
        <Title level={5}>性能指标</Title>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic 
              title="DNS解析时间" 
              value={metrics.dns_time ? metrics.dns_time * 1000 : 0} 
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="响应时间" 
              value={metrics.response_time ? metrics.response_time * 1000 : 0}
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="下载时间" 
              value={metrics.download_time ? metrics.download_time * 1000 : 0}
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="解析时间" 
              value={metrics.parse_time ? metrics.parse_time * 1000 : 0}
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="总时间" 
              value={metrics.total_time ? metrics.total_time * 1000 : 0}
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="HTML大小" 
              value={metrics.html_size ? metrics.html_size / 1024 : 0}
              suffix="KB"
              precision={2}
            />
          </Col>
        </Row>
      </div>
    );
  };

  const renderStats = () => {
    if (!stats) return null;

    return (
      <Card title="抓取统计" className="stats-card">
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic
              title="总URL数"
              value={stats.total_urls || 0}
              suffix="个"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="成功数"
              value={stats.success_count || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
              suffix="个"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="失败数"
              value={stats.failed_count || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
              suffix="个"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="平均抓取时间"
              value={stats.avg_time_per_page ? stats.avg_time_per_page * 1000 : 0}
              suffix="ms"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="平均页面大小"
              value={stats.avg_size_per_page ? stats.avg_size_per_page / 1024 : 0}
              suffix="KB"
              precision={2}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="总耗时"
              value={stats.total_time || 0}
              suffix="秒"
              precision={2}
            />
          </Col>
        </Row>

        <Title level={4} style={{ marginTop: 24 }}>按域名统计</Title>
        <Table
          dataSource={Object.entries(stats.domains || {}).map(([domain, data]: [string, any]) => ({
            domain,
            ...data,
            success_rate: data.count > 0 ? (data.success_count / data.count * 100).toFixed(2) : 0
          }))}
          columns={[
            {
              title: '域名',
              dataIndex: 'domain',
              key: 'domain',
            },
            {
              title: '总请求数',
              dataIndex: 'count',
              key: 'count',
            },
            {
              title: '成功率',
              dataIndex: 'success_rate',
              key: 'success_rate',
              render: (value: string) => (
                <Progress
                  percent={parseFloat(value) || 0}
                  size="small"
                  status={parseFloat(value) === 100 ? 'success' : 'active'}
                />
              ),
            },
            {
              title: '平均时间',
              dataIndex: 'avg_time',
              key: 'avg_time',
              render: (value: number) => value ? `${(value * 1000).toFixed(2)}ms` : '-',
            },
            {
              title: '平均大小',
              dataIndex: 'avg_size',
              key: 'avg_size',
              render: (value: number) => value ? `${(value / 1024).toFixed(2)}KB` : '-',
            },
          ]}
          pagination={false}
        />

        {stats.error_types && Object.keys(stats.error_types).length > 0 && (
          <>
            <Title level={4} style={{ marginTop: 24 }}>错误类型统计</Title>
            <Table
              dataSource={Object.entries(stats.error_types).map(([type, count]: [string, any]) => ({
                type,
                count,
              }))}
              columns={[
                {
                  title: '错误类型',
                  dataIndex: 'type',
                  key: 'type',
                },
                {
                  title: '出现次数',
                  dataIndex: 'count',
                  key: 'count',
                },
              ]}
              pagination={false}
            />
          </>
        )}
      </Card>
    );
  };

  const expandedRowRender = (record: any) => {
    return (
      <div className="expanded-content">
        {renderPerformanceMetrics(record.performance)}
        
        {record.images && record.images.length > 0 && (
          <div>
            <h4>图片内容（{record.images.length} 张）：</h4>
            <div className="image-grid">
              {record.images.map((img: string, index: number) => (
                <div key={index} className="image-item">
                  <Image
                    src={processImageUrl(img)}
                    alt={`爬取的图片 ${index + 1}`}
                    fallback="data:image/png;base64,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"
                  />
                  <div className="image-count">图片 {index + 1}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {record.text && (
          <div>
            <h4>文本内容：</h4>
            <Paragraph className="content-text" ellipsis={{ rows: 5, expandable: true, symbol: '展开' }}>
              {record.text}
            </Paragraph>
          </div>
        )}
      </div>
    )
  }

  const columns = [
    {
      title: '网址',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
    },
    {
      title: '页面大小',
      dataIndex: 'size',
      key: 'size',
      width: 120,
      render: (size: number) => size ? `${(size / 1024).toFixed(2)} KB` : '-',
    },
    {
      title: '抓取时间',
      dataIndex: 'time',
      key: 'time',
      width: 120,
      render: (time: number) => time ? `${time.toFixed(2)} 秒` : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 200,
      render: (status: string) => (
        <span style={{ color: status === '成功' ? '#52c41a' : '#f5222d' }}>
          {status}
        </span>
      ),
    },
  ]

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const response = await axios.post('http://localhost:5000/crawl', values)
      setCrawlResults(response.data.results)
      setStats(response.data.stats)
      message.success('抓取完成！')
    } catch (error) {
      message.error('抓取失败，请重试！')
    }
    setLoading(false)
  }

  return (
    <Layout className="layout">
      <Header>
        <h1 className="site-title">网络爬虫工具</h1>
      </Header>
      <Content>
        <Card title="爬虫配置" className="config-card">
          <Form
            form={form}
            name="crawl_config"
            onFinish={onFinish}
            layout="vertical"
          >
            <Form.Item
              name="urls"
              label="目标网址"
              rules={[{ required: true, message: '请输入要抓取的网址！' }]}
            >
              <Input.TextArea
                placeholder="请输入要抓取的网址，每行一个"
                rows={4}
              />
            </Form.Item>

            <Form.Item name="maxSize" label="最大页面大小 (KB)">
              <InputNumber min={1} max={10000} defaultValue={1000} />
            </Form.Item>

            <Form.Item name="contentType" label="内容类型">
              <Select defaultValue="all">
                <Option value="all">所有内容</Option>
                <Option value="images">仅图片</Option>
                <Option value="text">仅文本</Option>
              </Select>
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                icon={<CloudDownloadOutlined />}
                loading={loading}
                htmlType="submit"
                className="submit-button"
              >
                开始抓取
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {stats && renderStats()}

        <Card title="抓取结果" className="results-card">
          <Table
            columns={columns}
            dataSource={crawlResults}
            rowKey="url"
            loading={loading}
            expandable={{
              expandedRowRender,
              expandRowByClick: true,
            }}
            locale={{
              emptyText: <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无数据"
              />
            }}
          />
        </Card>
      </Content>
    </Layout>
  )
}

export default App