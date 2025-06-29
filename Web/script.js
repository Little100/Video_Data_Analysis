let isDarkTheme = false;
let trendChartInstance, followerChartInstance;
let allVideosData = [];
let allDanmakus = [];

function applyTheme(isDark) {
  isDarkTheme = isDark;
  document.body.classList.toggle("dark-theme", isDark);
  document.body.classList.toggle("light-theme", !isDark);

  const themeIcon = document.querySelector(".theme-icon");
  if (isDarkTheme) {
    themeIcon.innerHTML = `<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M17.78 17.78l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M17.78 6.22l1.42-1.42"/>`;
  } else {
    themeIcon.innerHTML = `<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>`;
  }
  updateChartsTheme();
}

function toggleTheme() {
  applyTheme(!isDarkTheme);
}

function detectSystemTheme() {
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark);

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (event) => {
    applyTheme(event.matches);
  });
}

function drawLineChart(canvas, data, monthlyDetails = {}) {
  if (trendChartInstance) trendChartInstance.destroy();
  const ctx = canvas.getContext("2d");

  const filteredDatasets = data.datasets.filter(
    (ds) =>
      ds.label.includes("累计播放量") ||
      ds.label.includes("每月播放量") ||
      ds.label.includes("累计视频发布数") ||
      ds.label.includes("累计点赞量")
  );

  if (filteredDatasets.length === 0) {
    console.error("没有找到播放量相关的数据集！");
    return;
  }

  trendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: filteredDatasets.map((ds) => {
        let borderColor, backgroundColor;

        if (ds.label.includes("每月播放量")) {
          borderColor = "#f97316";
          backgroundColor = "rgba(249, 115, 22, 0.1)";
        } else if (ds.label.includes("累计播放量")) {
          borderColor = "#14b8a6";
          backgroundColor = "rgba(20, 184, 166, 0.1)";
        } else if (ds.label.includes("累计点赞量")) {
          borderColor = "#ec4899";
          backgroundColor = "rgba(236, 72, 153, 0.1)";
        } else {
          borderColor = "#3b82f6";
          backgroundColor = "rgba(59, 130, 246, 0.1)";
        }

        return {
          ...ds,
          borderColor: borderColor,
          backgroundColor: backgroundColor,
          fill: false,
          tension: 0.4,
          pointRadius: 8,
          pointHoverRadius: 12,
          pointBackgroundColor: borderColor,
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          borderWidth: 3,
        };
      }),
    },
    options: getChartOptionsWithClick(true, monthlyDetails),
  });
}

function drawBarChart(canvas, data) {
  if (followerChartInstance) followerChartInstance.destroy();
  const ctx = canvas.getContext("2d");
  followerChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: data.datasets.map((ds) => ({ ...ds, backgroundColor: "#14b8a6" })),
    },
    options: getChartOptions(false),
  });
}

function formatLargeNumber(num) {
  if (num >= 100000000) return `${(num / 100000000).toFixed(2)}亿`;
  if (num >= 10000) return `${(num / 10000).toFixed(2)}万`;
  return num.toLocaleString();
}

function getChartOptions(enableYCallback = false, monthlyDetails = {}) {
  const textColor = isDarkTheme ? "#d1d5db" : "#374151";
  const gridColor = isDarkTheme ? "#374151" : "#e5e7eb";
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "point",
      intersect: false,
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        position: "nearest",
        xAlign: "center",
        yAlign: "bottom",
        caretPadding: 10,
        cornerRadius: 8,
        backgroundColor: "rgba(0, 0, 0, 0.9)",
        titleColor: "#ffffff",
        bodyColor: "#ffffff",
        borderColor: "#f97316",
        borderWidth: 2,
        displayColors: false,
        padding: 12,
        enabled: true,
        callbacks: {
          title: (context) => `${context[0].label} 月份数据`,
          label: (context) => {
            let label = context.dataset.label || "";
            if (label) label += ": ";
            if (context.parsed.y !== null) {
              label += formatLargeNumber(context.parsed.y);
            }
            return label;
          },
          afterLabel: (context) => {
            const datasetLabel = context.dataset.label;
            if (datasetLabel.includes("累计")) {
                return [];
            }

            const [year, month] = context.label.split('.').map(Number);
            const monthKey = `${year}-${String(month).padStart(2, '0')}`;
            const details = monthlyDetails[monthKey];
            if (!details) return [];

            let changeKey;
            if (datasetLabel.includes("播放量")) changeKey = 'views_change';
            else if (datasetLabel.includes("视频发布数")) changeKey = 'videos_change';
            else if (datasetLabel.includes("点赞量")) changeKey = 'likes_change';

            if (changeKey && details[changeKey] && details[changeKey] !== "N/A") {
                const change = details[changeKey];
                const isNegative = change.startsWith('-');
                const symbol = isNegative ? '🔻' : '🔺';
                return [`${symbol} 月度变化: ${change}`];
            }
            return [];
          }
        },
        bodyFont: {
            size: 14,
        },
        bodySpacing: 4
      },
    },
    scales: {
      x: {
        ticks: { color: textColor },
        grid: { color: gridColor },
      },
      y: {
        ticks: { color: textColor },
        grid: { color: gridColor },
      },
    },
  };

  if (enableYCallback) {
    options.scales.y.ticks.callback = (value) => formatLargeNumber(value);
  }
  return options;
}

function getChartOptionsWithClick(enableYCallback = false, monthlyDetails = {}) {
  const options = getChartOptions(enableYCallback, monthlyDetails);
  options.onClick = (event, elements) => {
    if (elements.length > 0) {
      const dataIndex = elements[0].index;
      const month = trendChartInstance.data.labels[dataIndex];
      showMonthlyVideoDetails(month);
    }
  };
  return options;
}

function showMonthlyVideoDetails(month) {
  console.log(`显示 ${month} 的月度视频详情`);

  const [year, monthNum] = month.split('.').map(Number);
  const monthKey = `${year}-${String(monthNum).padStart(2, '0')}`;

  const monthlyVideos = allVideosData.filter(video => video.publish_time.startsWith(monthKey));

  if (monthlyVideos.length === 0) {
      console.log(`在 ${month} 没有找到视频。`);
      return;
  }
  
  monthlyVideos.sort((a, b) => new Date(a.publish_time) - new Date(b.publish_time));

  const modal = document.getElementById("chartModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalCanvas = document.getElementById("modalChart");

  if (modal && modalCanvas && modalTitle) {
    if (modal.chartInstance) {
      modal.chartInstance.destroy();
      modal.chartInstance = null;
    }

    modalTitle.textContent = `${month} 月度视频播放量详情`;
    modal.style.display = "flex";

    const ctx = modalCanvas.getContext("2d");

    const monthlyChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: monthlyVideos.map(v => v.title),
        datasets: [
          {
            label: `播放量`,
            data: monthlyVideos.map(v => v.view_count),
            backgroundColor: "#f97316",
            borderColor: "#f97316",
            borderWidth: 1
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
          },
          tooltip: {
            callbacks: {
              title: (context) => {
                const index = context[0].dataIndex;
                return monthlyVideos[index].title;
              },
              label: (context) => {
                const index = context.dataIndex;
                const video = monthlyVideos[index];
                const lines = [];
                lines.push(`播放量: ${formatLargeNumber(video.view_count)}`);
                lines.push(`点赞量: ${formatLargeNumber(video.like_count)}`);
                lines.push(`发布于: ${video.publish_time}`);
                return lines;
              },
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "播放量",
            },
            ticks: {
              color: isDarkTheme ? "#d1d5db" : "#374151",
              callback: (value) => formatLargeNumber(value),
            },
            grid: {
              color: isDarkTheme ? "#374151" : "#e5e7eb",
            },
          },
          y: {
            ticks: {
              color: isDarkTheme ? "#d1d5db" : "#374151",
            },
            grid: {
              color: isDarkTheme ? "#374151" : "#e5e7eb",
            },
          },
        },
      },
    });

    modal.chartInstance = monthlyChart;
  }
}

function updateChartsTheme(monthlyDetails = {}) {
  if (trendChartInstance) {
    Object.assign(trendChartInstance.options, getChartOptionsWithClick(true, monthlyDetails));
    trendChartInstance.update();
  }
  if (followerChartInstance) {
    Object.assign(followerChartInstance.options, getChartOptions(false, monthlyDetails));
    followerChartInstance.update();
  }
}

async function loadDashboardData() {
  try {
    const response = await fetch(`dashboard_data.json?v=${new Date().getTime()}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();

    allVideosData = data.all_videos || [];
    allDanmakus = data.all_danmakus || [];
    const monthlyDetails = data.monthly_details || {};

    document.querySelectorAll(".stat-card").forEach((card) => {
      const titleElement = card.querySelector(".stat-title");
      if (!titleElement) return;

      const title = titleElement.textContent;
      const valueElement = card.querySelector(".stat-value");
      if (!valueElement) return;

      const summary = data.summary;
      if (title.includes("粉丝数")) {
        valueElement.textContent = summary.total_fans;
      } else if (title.includes("总播放量")) {
        valueElement.textContent = summary.total_views;
      } else if (title.includes("累计视频数")) {
        valueElement.textContent = summary.total_videos;
      } else if (title.includes("总点赞量")) {
        valueElement.textContent = summary.total_likes;
      } else if (title.includes("近一个月涨粉量")) {
        valueElement.textContent = summary.last_month_fans || "10";
        const changeElement = card.querySelector(".stat-change span:first-of-type");
        if (changeElement) changeElement.textContent = summary.last_month_fans_change || "N/A";
      } else if (title.includes("近一个月播放量")) {
        valueElement.textContent = summary.last_month_views;
        const changeElement = card.querySelector(".stat-change span:first-of-type");
        if (changeElement) changeElement.textContent = summary.last_month_views_change || "N/A";
      } else if (title.includes("近一个月点赞量")) {
        valueElement.textContent = summary.last_month_likes || "0";
        const changeElement = card.querySelector(".stat-change span:first-of-type");
        if (changeElement) changeElement.textContent = summary.last_month_likes_change || "N/A";
      } else if (title.includes("近一个月发布视频数量")) {
        valueElement.textContent = summary.last_month_videos || "2";
        const changeElement = card.querySelector(".stat-change span:first-of-type");
        if (changeElement) changeElement.textContent = summary.last_month_videos_change || "N/A";
      }
    });

    updateFollowerChartTitle(data.summary.total_fans);
    initCharts(data.trend_chart, data.follower_chart, monthlyDetails);
    renderVideoPerformanceList(data.video_performance);
    initDanmaku();
    updateChartsTheme(monthlyDetails);
  } catch (error) {
    console.error("无法加载仪表板数据:", error);
    document.querySelector(".dashboard-container").innerHTML =
      `<p style="color: red; text-align: center;">加载数据失败，请检查后台服务是否正常运行。</p>`;
  }
}

function updateFollowerChartTitle(followerCount) {
  const followerElement = document.querySelector(".chart-card:nth-child(2) .follower-count");
  if (followerElement) followerElement.textContent = followerCount;
}

function initCharts(trendData, followerData, monthlyDetails = {}) {
  const trendCanvas = document.getElementById("trendChart");
  if (trendCanvas && trendData) {
    drawLineChart(trendCanvas, trendData, monthlyDetails);
  }

  const followerCanvas = document.getElementById("followerChart");
  if (followerCanvas && followerData) {
    drawBarChart(followerCanvas, followerData);
  }
}

function expandChart(chartType) {
    const modal = document.getElementById("chartModal");
    const modalCanvas = document.getElementById("modalChart");

    if (modal && modalCanvas) {
        if (modal.chartInstance) {
            modal.chartInstance.destroy();
            modal.chartInstance = null;
        }

        modal.style.display = "flex";

        let originalChart;
        if (chartType === 'trend') {
            originalChart = trendChartInstance;
        } else if (chartType === 'follower') {
            originalChart = followerChartInstance;
        }

        if (originalChart) {
            const ctx = modalCanvas.getContext("2d");
            
            const clonedData = JSON.parse(JSON.stringify(originalChart.data));
            clonedData.datasets.forEach((ds, index) => {
                const originalDs = originalChart.data.datasets[index];
                if (typeof originalDs.borderColor === 'string') {
                    ds.borderColor = originalDs.borderColor;
                } else {
                    ds.borderColor = '#3b82f6';
                }
                if (typeof originalDs.backgroundColor === 'string') {
                    ds.backgroundColor = originalDs.backgroundColor;
                } else {
                    ds.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });

            const clonedOptions = JSON.parse(JSON.stringify(originalChart.options));
            clonedOptions.maintainAspectRatio = false;
            if (!clonedOptions.plugins) clonedOptions.plugins = {};
            clonedOptions.plugins.legend = { display: true, position: 'top' };


            modal.chartInstance = new Chart(ctx, {
                type: originalChart.config.type,
                data: clonedData,
                options: clonedOptions,
            });
        }
    }
}

function closeModal() {
  const modal = document.getElementById("chartModal");
  if (modal) {
    if (modal.chartInstance) {
      modal.chartInstance.destroy();
      modal.chartInstance = null;
    }
    modal.style.display = "none";
  }
}

function initDanmaku() {
  const container = document.getElementById('danmaku-container');
  if (!container || !allDanmakus || allDanmakus.length === 0) {
    return;
  }

  setInterval(() => {
    const danmakuData = allDanmakus[Math.floor(Math.random() * allDanmakus.length)];
    if (!danmakuData) return;

    const danmaku = document.createElement('div');
    danmaku.className = 'danmaku';
    danmaku.textContent = danmakuData.text;
    danmaku.title = `来自: ${danmakuData.video_title}`;
    
    danmaku.style.top = `${Math.random() * 90}%`;
    
    const duration = Math.random() * 10 + 8;
    danmaku.style.animationDuration = `${duration}s`;

    container.appendChild(danmaku);

    setTimeout(() => {
      danmaku.remove();
    }, duration * 1000);

  }, 500);
}

document.addEventListener("DOMContentLoaded", () => {
  detectSystemTheme();
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
  loadDashboardData();
});

function renderVideoPerformanceList(videoData) {
  const listContainer = document.getElementById("video-performance-list");
  if (!listContainer) return;

  if (!videoData || !Array.isArray(videoData) || videoData.length === 0) {
    listContainer.innerHTML = '<p style="color: var(--text-secondary);">暂无符合条件的视频表现数据（播放量>=10000）。</p>';
    return;
  }

  listContainer.innerHTML = "";

  const maxRate = Math.max(...videoData.map((v) => v.like_rate), 0);

  videoData.slice(0, 15).forEach((video) => {
    const item = document.createElement("div");
    item.className = "video-perf-item";

    const title = document.createElement("div");
    title.className = "video-perf-title";
    title.textContent = video.title;
    title.title = video.title;

    const barContainer = document.createElement("div");
    barContainer.className = "video-perf-bar-container";

    const bar = document.createElement("div");
    bar.className = "video-perf-bar";
    const barWidth = maxRate > 0 ? (video.like_rate / maxRate) * 100 : 0;
    bar.style.width = `${barWidth}%`;

    const rate = document.createElement("div");
    rate.className = "video-perf-rate";
    rate.textContent = `${video.like_rate.toFixed(2)}%`;

    const views = document.createElement("div");
    views.className = "video-perf-extra";
    views.textContent = `▶ ${formatLargeNumber(video.views)}`;

    const likes = document.createElement("div");
    likes.className = "video-perf-extra";
    likes.textContent = `👍 ${formatLargeNumber(video.likes)}`;

    barContainer.appendChild(bar);
    barContainer.appendChild(rate);
    item.appendChild(title);
    item.appendChild(barContainer);
    item.appendChild(views);
    item.appendChild(likes);
    listContainer.appendChild(item);
  });
}
