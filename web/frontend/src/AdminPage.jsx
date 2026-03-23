import { useState, useEffect } from "react";
import { getAdminMetrics } from "./api";

export default function AdminPage() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAdminMetrics()
      .then((data) => setMetrics(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-4 border-gray-700 border-t-anchor-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950/50 border border-red-800 rounded-lg p-4 mt-6">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className="pb-12 mt-6">
      <h2 className="text-xl font-bold text-white mb-6">Admin Dashboard</h2>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Scans" value={metrics.total_scans} />
        <StatCard label="Unique Users" value={metrics.unique_users} />
        <StatCard label="Avg Score" value={metrics.average_score} />
        <StatCard label="Error Rate" value={`${metrics.error_rate}%`} />
      </div>

      {/* Scans by day */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6 mb-6">
        <h3 className="text-white font-semibold mb-4">Scans Per Day (Last 30 Days)</h3>
        {metrics.scans_by_day.length === 0 ? (
          <p className="text-gray-500 text-sm">No data yet</p>
        ) : (
          <div className="flex items-end gap-1 h-32">
            {metrics.scans_by_day
              .slice()
              .reverse()
              .map((day) => {
                const max = Math.max(
                  ...metrics.scans_by_day.map((d) => d.count),
                  1
                );
                const height = Math.max((day.count / max) * 100, 4);
                return (
                  <div
                    key={day.date}
                    className="flex-1 min-w-[8px] group relative"
                  >
                    <div
                      className="bg-anchor-500 rounded-t w-full transition-all hover:bg-anchor-400"
                      style={{ height: `${height}%` }}
                    />
                    <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                      {day.date}: {day.count}
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Most scanned repos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-white font-semibold mb-4">Most Scanned Repos</h3>
          {metrics.most_scanned_repos.length === 0 ? (
            <p className="text-gray-500 text-sm">No data yet</p>
          ) : (
            <div className="space-y-2">
              {metrics.most_scanned_repos.map((repo, i) => (
                <div
                  key={repo.repo_url}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-300 truncate max-w-[70%]">
                    <span className="text-gray-500 mr-2">{i + 1}.</span>
                    {repo.repo_url.replace("https://github.com/", "")}
                  </span>
                  <span className="text-anchor-400 font-medium">
                    {repo.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent scans */}
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-white font-semibold mb-4">Recent Scans</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {metrics.recent_scans.map((scan) => (
              <div
                key={scan.scan_id}
                className="flex items-center justify-between text-sm border-b border-gray-800 pb-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-gray-300 truncate">
                    {scan.repo_url.replace("https://github.com/", "")}
                  </div>
                  <div className="text-gray-500 text-xs">
                    {scan.username || "anonymous"} &middot;{" "}
                    {new Date(scan.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  {scan.score != null && (
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        scan.score >= 80
                          ? "bg-green-500 text-white"
                          : scan.score >= 60
                            ? "bg-anchor-500 text-white"
                            : scan.score >= 40
                              ? "bg-yellow-500 text-white"
                              : "bg-red-500 text-white"
                      }`}
                    >
                      {scan.score}
                    </span>
                  )}
                  <span
                    className={`text-xs ${
                      scan.status === "complete"
                        ? "text-green-400"
                        : scan.status === "error"
                          ? "text-red-400"
                          : "text-gray-400"
                    }`}
                  >
                    {scan.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
      <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="text-white text-2xl font-bold">{value}</p>
    </div>
  );
}
