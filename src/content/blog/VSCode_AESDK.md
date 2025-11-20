---
title: 在VSCode(windows)内配置AE插件开发环境(AESDK)
description: 本文档介绍如何在Windows系统的VSCode中配置Adobe After Effects插件开发环境，主要内容是编译环境的配置。
pubDate: 2025-11-15
image: /image/PIC_AESDK.jpg
categories:
  - dev
tags:
  - dev
  - MSVC
  - AE
  - AE插件
  - vscode
---

这篇博客主要讲述了我在VSCode里配置AESDK开发环境的过程。

## 前言

现在网络上大多数关于配置AE SDK的教程都是基于Visual Studio的，且官方提供的模板也是使用的VS的项目文件进行配置，但对于我个人来讲，更喜欢使用VSCode进行开发，而且本人对于直接提供完整的VS项目文件的黑盒式编译流程有些无法接受，这会影响对AE插件工作流程的理解。我个人是喜欢在理解其底层原理的基础上进行开发的，这能让我感觉对整个开发流程有更好的掌控感。因此我决定在VSCode上从头构建一个AE插件的开发环境。

## 环境准备

1. **安装VSCode**：确保你已经安装了最新版本的VSCode。
2. **安装MSVC编译环境**：建议安装Visual Studio，我们将在稍后调用随VS安装的MSVC编译器进行编译。
3. **下载AE SDK**：从Adobe官方网站下载After Effects SDK。

## 理解编译流程

在开始配置之前，我们需要理解AE插件的编译流程。AE插件通常包含资源文件和代码文件，资源文件需要经过特定的处理才能被AE识别。 以下是一个典型的编译流程：
1. 使用`cl`编译器将资源脚本文件（`.r`）预处理为中间文件（`.rr`）。
2. 使用`PiPLTool.exe`将中间文件转换为资源文件（`.rrc`）。
3. 使用`cl`编译器将资源文件转换为最终的资源文件（`.rc`）。
4. 使用`rc`工具将资源文件编译为二进制资源文件（`.res`）。
5. 使用`cl`编译器将代码文件和资源文件链接生成最终的AE插件（`.aex`）。

## 配置VSCode任务

下面是一个示例的`tasks.json`配置文件，展示了如何在VSCode中配置上述编译流程：

``` json
{
  "version": "2.0.0",
  "windows": {
    "options": {
      "shell": {
        "executable": "cmd.exe",
        "args": [
          "/c",
        ]
      },
      "cwd": "${workspaceFolder}",
    }
  },
  "tasks": [
    {
      "label": "test",
      "type": "cppbuild",
      "command": "CALL",
      "args": [
        "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\Common7\\Tools\\VsDevCmd.bat",

        "&&", "cl",
        "${workspaceFolder}/src/${fileBasenameNoExtension}PiPL.r",
        "/nologo", "/EP", "/P",
        "/Fi${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rr",

        "&&", "${workspaceFolder}/AESDK/Resources/PiPLTool.exe",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rr",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rrc",

        "&&", "cl",
        "/nologo", "/EP",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rrc",
        ">",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rc",

        "&&", "rc",
        "/nologo", "/fo",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.res",
        "${workspaceFolder}/build/res/${fileBasenameNoExtension}PiPL.rc",

        "&&", "cl",
        "${workspaceFolder}/src/${fileBasename}",
        "/nologo", "/EHsc", "/O2", "/LD", "/MD",
        "/D", "MSWindows", "/D", "WIN32", "/D", "_WINDOWS",
        "/link",
        "${workspaceFolder}/build/${fileBasenameNoExtension}PiPL.res",
        "/OUT:${workspaceFolder}/build/${fileBasenameNoExtension}.aex"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always"
      },
      "options": {
        "env": {
          "INCLUDE": "${workspaceFolder}\\AESDK\\Headers;${workspaceFolder}\\AESDK\\Headers\\SP;${workspaceFolder}\\AESDK\\Util;${workspaceFolder}\\AESDK\\Resources;${env:INCLUDE}"
          // 这里需要你自行根据你的AESDK路径进行调整，确保包含了所有必要的头文件路径
        }
      }
    }
  ]
}
```

可以看到，我们先调用了VS的开发者命令行脚本来设置编译环境变量，然后还在末尾的`options.env`中设置了`INCLUDE`环境变量，确保编译器能够找到AE SDK的头文件。随后，我们按照之前描述的编译流程一步步处理资源文件和代码文件，最终生成AE插件。
可以确定的是，我们需要AE SD的头文件主要路径包括：

- `\Headers`
- `\Headers\SP`
- `\Util`
- `\Resources`

而其中Resources目录提供的文件主要用于资源文件的生成。

## 文件结构

用该方案配置的项目文件结构大致如下：

```
project-root/
├── AESDK/                  # AE SDK目录
│   ├── Headers/
│   │   └── SP/
│   ├── Resources/
│   └── Util/
├── src/                    # 源代码目录
│   ├── MyPlugin.cpp        # 插件源代码文件
│   ├── MyPlugin.h          # 插件源代码头文件
│   └── MyPluginPiPL.r      # 插件资源文件
├── build/                  # 构建输出目录
│   ├── res/                # 资源中间文件目录
│   └── MyPlugin.aex        # 最终生成的AE插件文件
├── .vscode/                # VSCode配置目录
│   └── tasks.json          # VSCode任务配置文件
└── README.md               # 项目说明文件
```

## 结语
通过以上步骤，我们成功地在VSCode中配置了AE插件的开发环境。希望这篇博客能帮助到有类似需求的开发者。如果你有任何问题或建议，欢迎和我交流！

喵