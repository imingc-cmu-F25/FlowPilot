import { Link } from "react-router";
import {
  Zap,
  Clock,
  Webhook,
  Mail,
  Bell,
  Code,
  ArrowRight,
  CheckCircle,
  Activity,
} from "lucide-react";
import { DashboardTopBar } from "../components/DashboardTopBar";
import { IconCard } from "../components/IconCard";

const features = [
  {
    icon: Clock,
    title: "Time-based Triggers",
    description:
      "Schedule workflows to run automatically at specific times or intervals",
  },
  {
    icon: Webhook,
    title: "Webhook Integration",
    description:
      "Connect with external services and trigger workflows from anywhere",
  },
  {
    icon: Mail,
    title: "Email Actions",
    description: "Send automated emails as part of your workflow",
  },
  {
    icon: Code,
    title: "API Integrations",
    description: "Connect to any API and automate complex tasks",
  },
];

const benefits = [
  "Visual workflow builder with drag-and-drop",
  "Real-time execution monitoring",
  "Detailed logs and analytics",
  "Monthly AI-powered reports",
  "Unlimited workflow executions",
  "99.9% uptime guarantee",
];

export function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      <DashboardTopBar />

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="text-center">
          <h1 className="mb-6 text-5xl font-bold text-gray-900">
            Automate Your Workflow
            <br />
            in Minutes
          </h1>
          <p className="mx-auto mb-8 max-w-2xl text-xl text-gray-600">
            FlowPilot helps students streamline their daily tasks with powerful
            workflow automation. No coding required.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white transition-colors hover:bg-blue-700"
            >
              Login
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              to="/signup"
              className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Register
            </Link>
          </div>
        </div>

        <div className="mt-20 overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50 to-purple-50 p-8 shadow-lg">
          <div className="mx-auto max-w-4xl">
            <div className="relative h-96 rounded-lg bg-white p-6 shadow-xl">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="flex h-40 w-40 items-center justify-center rounded-full bg-blue-100">
                      <Zap className="h-20 w-20 text-blue-600" />
                    </div>
                  </div>
                  <div className="absolute -left-12 -top-12">
                    <IconCard
                      icon={Clock}
                      label="Time Trigger"
                      iconClassName="h-6 w-6 text-purple-600"
                    />
                  </div>
                  <div className="absolute -right-12 -top-12">
                    <IconCard
                      icon={Webhook}
                      label="Webhook"
                      iconClassName="h-6 w-6 text-green-600"
                    />
                  </div>
                  <div className="absolute -bottom-12 -left-12">
                    <IconCard
                      icon={Mail}
                      label="Send Email"
                      iconClassName="h-6 w-6 text-blue-600"
                    />
                  </div>
                  <div className="absolute -bottom-12 -right-12">
                    <IconCard
                      icon={Bell}
                      label="Notify"
                      iconClassName="h-6 w-6 text-orange-600"
                    />
                  </div>
                  <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                    <Activity className="h-8 w-8 text-blue-600" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold text-gray-900">
              Everything You Need to Automate
            </h2>
            <p className="text-lg text-gray-600">
              Powerful features designed for students and productivity
              enthusiasts
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50">
                    <Icon className="h-6 w-6 text-blue-600" />
                  </div>
                  <h3 className="mb-2 text-lg font-semibold text-gray-900">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-gray-600">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
            <div>
              <h2 className="mb-6 text-3xl font-bold text-gray-900">
                Why Choose FlowPilot?
              </h2>
              <p className="mb-8 text-lg text-gray-600">
                Built specifically for students who want to save time and focus
                on what matters most. FlowPilot makes automation accessible to
                everyone.
              </p>
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-50">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <span className="text-gray-700">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-gradient-to-br from-purple-50 to-blue-50 p-8">
              <div className="relative h-80 w-full">
                <div className="absolute left-1/4 top-1/4">
                  <IconCard
                    icon={CheckCircle}
                    label="Workflow Active"
                    iconClassName="h-5 w-5 text-green-600"
                  />
                </div>
                <div className="absolute right-1/4 top-1/3">
                  <IconCard
                    icon={Activity}
                    label="Running"
                    iconClassName="h-5 w-5 text-blue-600"
                  />
                </div>
                <div className="absolute bottom-1/4 left-1/3">
                  <IconCard
                    icon={Code}
                    label="Automated"
                    iconClassName="h-5 w-5 text-purple-600"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-gray-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">
                FlowPilot
              </span>
            </div>
            <p className="text-sm text-gray-600">
              © 2026 FlowPilot. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
