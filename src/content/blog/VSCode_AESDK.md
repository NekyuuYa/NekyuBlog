---
title: 在VSCode(windows)内配置AE插件开发环境(AESDK)
description: 本文档介绍如何在Windows系统的VSCode中配置Adobe After Effects插件开发环境，主要内容是编译环境的配置。
pubDate: 2025-11-15
image: /image/PIC_AESDK.jpg
categories:
  - dev
tags:
  - blog
  - dev
  - MSVC
  - AE
  - vscode
---

这篇博客主要讲述了我在VSCode里配置AESDK开发环境的过程。

## 前言

现在网络上大多数关于配置`AE SDK`的教程都是基于Visual Studio的，且官方提供的模板也是使用的VS的项目文件进行配置，但对于我个人来讲，更喜欢使用VSCode进行开发，而且本人对于使用VS这种完全是黑盒式的编译流程有些无法接受，觉得这会影响我对AE插件工作流程的理解。我个人是喜欢在理解其底层原理的基础上进行开发的，这能让我感觉对整个开发流程有更好的掌控感。因此我决定在VSCode上从头构建一个AE插件的开发环境。

## 环境准备

1. **安装VSCode**：确保你已经安装了最新版本的VSCode。
2. **安装C++编译器**：建议安装Visual Studio，我们将在稍后调用随VS安装的MSVC编译器进行编译。
3. **下载AE SDK**：从Adobe官方网站下载After Effects SDK。
