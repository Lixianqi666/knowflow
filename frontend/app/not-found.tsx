import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-7xl font-bold text-gray-200 mb-4">404</div>
        <p className="text-gray-500 mb-6">页面不存在</p>
        <Link
          href="/"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
